# Brand Radar — Архитектура

## Общая схема данных (E2E pipeline)

```
                                    PostgreSQL                          ClickHouse
                                 (source of truth,                   (аналитика,
                                  CRUD, ML-результаты,                spike-детекция)
                                  эмбеддинги, дедуп)

[Источники]       [Парсеры]            │                                    │
                                       │                                    │
Telegram ──┐                     ┌─────┴──────┐                             │
VK ────────┤──► Collector ──────►│ raw_posts  │                             │
Дзен ──────┤    Workers          │   (PG)     │                             │
RSS ───────┘    (asyncio)        └─────┬──────┘                             │
                                       │                                    │
                                       ▼                                    │
                                 ┌───────────┐     sync (INSERT)      ┌─────┴──────────┐
                                 │ ML Worker │────────────────────────►│ mention_events │
                                 └─────┬─────┘                        │   (ClickHouse) │
                                       │                              └────────────────┘
                                       ▼                                    │
                                 ┌───────────┐                              │
                                 │ mentions  │                              ▼
                                 │ (PG +     │                        ┌───────────────┐
                                 │  pgvector)│                        │ Spike Detector│
                                 └─────┬─────┘                        │ (CH запросы)  │
                                       │                              └───────┬───────┘
                                       │                                      │
                                       ▼                                      ▼
                                 ┌───────────┐                          ┌──────────┐
                                 │ dedup_    │                          │ alerts   │
                                 │ groups(PG)│                          │ (PG)     │
                                 └───────────┘                          └──────────┘
                                       │                                      │
                                       ▼                                      ▼
                               ┌──────────────┐
                               │  FastAPI     │◄──── UI запрашивает ленту, аналитику, алерты
                               │  REST API    │
                               └──────────────┘
```

---

## 1. Что лежит в PostgreSQL и почему

PG — **source of truth**. Всё, что нужно для CRUD, отображения карточек, ML-результатов, дедупликации.

### Таблица `projects` — настройки бренда

```sql
CREATE TABLE projects (
    id          serial PRIMARY KEY,
    name        text NOT NULL,                -- "Сбербанк"
    keywords    text[] NOT NULL,              -- {"сбербанк", "sberbank", "сбер"}
    exclude_keywords text[] DEFAULT '{}',     -- {"сберкот", "сберкнижка"}
    risk_words  text[] DEFAULT '{}',          -- {"утечка", "мошенники", "сбой"}
    created_at  timestamptz DEFAULT now()
);
```
**Почему PG**: это конфигурация, редко меняется, нужны FK на всех остальных таблицах.

### Таблица `sources` — откуда парсим

```sql
CREATE TABLE sources (
    id              serial PRIMARY KEY,
    project_id      int REFERENCES projects(id),
    source_type     text NOT NULL,          -- "telegram" | "vk" | "dzen" | "rss"
    source_config   jsonb NOT NULL,         -- {"channel": "@banksta"} или {"group_id": 12345}
    is_active       bool DEFAULT true,
    poll_interval_s int DEFAULT 300,        -- как часто опрашивать (сек)
    last_collected_at timestamptz,
    last_error      text,                   -- последняя ошибка (для health)
    created_at      timestamptz DEFAULT now()
);
```
**Почему PG**: CRUD, связь с проектом, нужно обновлять `last_collected_at` при каждом сборе.

### Таблица `raw_posts` — сырые данные с парсеров

```sql
CREATE TABLE raw_posts (
    id              bigserial PRIMARY KEY,
    source_id       int REFERENCES sources(id),
    external_id     text NOT NULL,              -- id поста в источнике
    url             text,
    title           text,
    text            text NOT NULL,
    author          text,
    published_at    timestamptz NOT NULL,
    collected_at    timestamptz DEFAULT now(),
    raw_meta        jsonb DEFAULT '{}',         -- views, reposts, likes и т.д.
    ml_processed    bool DEFAULT false,         -- обработан ли ML

    UNIQUE(source_id, external_id)              -- точная дедупликация
);

CREATE INDEX idx_raw_posts_unprocessed ON raw_posts(ml_processed) WHERE NOT ml_processed;
```
**Почему PG**: это рабочая таблица, ML-воркер берёт необработанные записи (`ml_processed = false`).
**Точная дедупликация**: UNIQUE constraint — один и тот же пост из одного источника не сохранится дважды.

### Таблица `mentions` — посты после ML-обработки

```sql
CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector

CREATE TABLE mentions (
    id                  bigserial PRIMARY KEY,
    raw_post_id         bigint UNIQUE REFERENCES raw_posts(id),
    project_id          int REFERENCES projects(id),

    -- === ML результаты (всегда сохраняем label + score) ===
    relevance_score     float NOT NULL,         -- 0.0 .. 1.0
    relevance_label     text NOT NULL,          -- "relevant" | "irrelevant"
    sentiment_score     float NOT NULL,         -- -1.0 .. 1.0
    sentiment_label     text NOT NULL,          -- "positive" | "neutral" | "negative"
    has_risk_words      bool DEFAULT false,     -- содержит risk_words из проекта

    -- === Эмбеддинг для семантической дедупликации ===
    embedding           vector(384) NOT NULL,   -- sentence-transformers output

    -- === Дедупликация ===
    dedup_group_id      bigint REFERENCES dedup_groups(id),
    is_primary          bool DEFAULT true,      -- показывать ли в ленте как основной

    processed_at        timestamptz DEFAULT now()
);

-- Индекс для быстрого поиска ближайших эмбеддингов (дедупликация)
CREATE INDEX idx_mentions_embedding ON mentions
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Индекс для ленты: релевантные, отсортированные по времени
CREATE INDEX idx_mentions_feed ON mentions(project_id, processed_at DESC)
    WHERE relevance_label = 'relevant' AND is_primary = true;
```

**Почему PG + pgvector**:
- ML-результаты привязаны 1:1 к raw_post → нужен FK → реляционная БД
- Эмбеддинги хранятся рядом с данными → поиск ближайших соседей через `<=>` оператор pgvector
- Не нужен отдельный vector store (Qdrant/Pinecone) — всё в одном месте, проще на олимпиаде

### Таблица `dedup_groups` — группы семантических дубликатов

```sql
CREATE TABLE dedup_groups (
    id                          bigserial PRIMARY KEY,
    project_id                  int REFERENCES projects(id),
    representative_mention_id   bigint,     -- самый ранний/авторитетный пост
    mention_count               int DEFAULT 1,
    created_at                  timestamptz DEFAULT now()
);
```
**Почему PG**: группа — это связь между mentions, нужны FK и JOIN для отображения на UI.

### Таблица `alerts` — spike-алерты

```sql
CREATE TABLE alerts (
    id              serial PRIMARY KEY,
    project_id      int REFERENCES projects(id),
    alert_type      text NOT NULL,          -- "negative_spike" | "volume_spike" | "risk_word_spike"
    title           text NOT NULL,
    message         text,
    severity        text DEFAULT 'medium',  -- "low" | "medium" | "high"
    mention_ids     bigint[],               -- какие посты вызвали алерт
    triggered_at    timestamptz DEFAULT now(),
    cooldown_until  timestamptz,            -- не алертить повторно до
    is_read         bool DEFAULT false
);
```
**Почему PG**: CRUD, отметка "прочитано", связь с mentions.

### Таблица `events` — журнал событий

```sql
CREATE TABLE events (
    id          bigserial PRIMARY KEY,
    project_id  int,
    event_type  text NOT NULL,      -- "collector_started", "collector_error",
                                    -- "ml_processed", "spike_detected", "alert_sent"
    payload     jsonb DEFAULT '{}',
    created_at  timestamptz DEFAULT now()
);

CREATE INDEX idx_events_lookup ON events(project_id, created_at DESC);
```
**Почему PG**: append-only лог, простые SELECT с пагинацией.

---

## 2. Что лежит в ClickHouse и почему

CH — **аналитический движок**. Не source of truth. Данные синхронизируются из PG после ML-обработки.

### Таблица `mention_events` — денормализованные факты

```sql
CREATE TABLE mention_events (
    mention_id      UInt64,
    project_id      UInt32,
    source_type     LowCardinality(String),     -- "telegram", "vk"
    source_id       UInt32,
    author          String,

    -- ML поля (копия из PG)
    relevance_score Float32,
    relevance_label LowCardinality(String),
    sentiment_score Float32,
    sentiment_label LowCardinality(String),
    has_risk_words  UInt8,                      -- 0/1
    is_primary      UInt8,

    -- Временные метки
    published_at    DateTime,
    collected_at    DateTime,
    processed_at    DateTime,

    -- Dedup
    dedup_group_id  UInt64
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(published_at)
ORDER BY (project_id, published_at, mention_id);
```

**Почему именно эти поля в CH**:
- Денормализовано специально — CH любит wide таблицы без JOIN
- `LowCardinality` для строк с малым числом уникальных значений → сжатие
- `ORDER BY (project_id, published_at)` — все запросы будут по проекту + окну времени
- `PARTITION BY toYYYYMM` — старые месяцы можно дропнуть

### Синхронизация PG → CH

```python
# После ML-обработки батча, вставляем в CH
async def sync_to_clickhouse(mentions: list[Mention], raw_posts: dict):
    rows = []
    for m in mentions:
        rp = raw_posts[m.raw_post_id]
        rows.append({
            "mention_id": m.id,
            "project_id": m.project_id,
            "source_type": rp.source.source_type,
            "source_id": rp.source_id,
            "author": rp.author or "",
            "relevance_score": m.relevance_score,
            "relevance_label": m.relevance_label,
            "sentiment_score": m.sentiment_score,
            "sentiment_label": m.sentiment_label,
            "has_risk_words": int(m.has_risk_words),
            "is_primary": int(m.is_primary),
            "published_at": rp.published_at,
            "collected_at": rp.collected_at,
            "processed_at": m.processed_at,
            "dedup_group_id": m.dedup_group_id or 0,
        })
    ch_client.insert("mention_events", rows)
```

---

## 3. Примеры запросов к ClickHouse (аналитика)

### Spike Detection — всплеск негатива за последние 30 минут vs baseline

```sql
-- Текущее окно: сколько негативных за последние 30 мин
SELECT count(*) AS current_count
FROM mention_events
WHERE project_id = {project_id}
  AND sentiment_label = 'negative'
  AND is_primary = 1
  AND published_at >= now() - INTERVAL 30 MINUTE;

-- Baseline: средний count за 30-минутные окна за последние 7 дней
SELECT avg(cnt) AS baseline_count
FROM (
    SELECT toStartOfThirtyMinute(published_at) AS window,
           count(*) AS cnt
    FROM mention_events
    WHERE project_id = {project_id}
      AND sentiment_label = 'negative'
      AND is_primary = 1
      AND published_at >= now() - INTERVAL 7 DAY
      AND published_at < now() - INTERVAL 30 MINUTE
    GROUP BY window
);

-- Spike если current_count > baseline_count * 3
```

### График тональности по дням (для UI — экран аналитики)

```sql
SELECT
    toDate(published_at) AS day,
    sentiment_label,
    count(*) AS cnt
FROM mention_events
WHERE project_id = {project_id}
  AND is_primary = 1
  AND relevance_label = 'relevant'
  AND published_at >= now() - INTERVAL 30 DAY
GROUP BY day, sentiment_label
ORDER BY day;

-- Результат:
-- day        | sentiment_label | cnt
-- 2026-03-01 | positive        | 45
-- 2026-03-01 | neutral         | 120
-- 2026-03-01 | negative        | 12
-- 2026-03-02 | positive        | 38
-- ...
```

### Топ источников по негативу (для UI — понять откуда идёт негатив)

```sql
SELECT
    source_type,
    source_id,
    count(*) AS negative_count,
    avg(sentiment_score) AS avg_sentiment
FROM mention_events
WHERE project_id = {project_id}
  AND sentiment_label = 'negative'
  AND is_primary = 1
  AND published_at >= now() - INTERVAL 7 DAY
GROUP BY source_type, source_id
ORDER BY negative_count DESC
LIMIT 10;
```

### Объём упоминаний по часам (для spike-визуализации)

```sql
SELECT
    toStartOfHour(published_at) AS hour,
    count(*) AS total,
    countIf(sentiment_label = 'negative') AS negative,
    countIf(has_risk_words = 1) AS with_risk_words
FROM mention_events
WHERE project_id = {project_id}
  AND is_primary = 1
  AND published_at >= now() - INTERVAL 48 HOUR
GROUP BY hour
ORDER BY hour;
```

### Скорость сбора (health/мониторинг лага)

```sql
SELECT
    source_type,
    avg(dateDiff('second', published_at, collected_at)) AS avg_lag_sec,
    max(dateDiff('second', published_at, collected_at)) AS max_lag_sec
FROM mention_events
WHERE project_id = {project_id}
  AND collected_at >= now() - INTERVAL 1 HOUR
GROUP BY source_type;
```

---

## 4. Полный пайплайн данных (пошагово)

```
ЭТАП 1: СБОР
═══════════════════════════════════════════════════════════════
  Collector Worker (каждые N сек для каждого source):
    1. Читает source.source_config из PG
    2. Запрашивает API/парсит HTML источника
    3. Для каждого поста:
       INSERT INTO raw_posts (...) ON CONFLICT (source_id, external_id) DO NOTHING
       ── если конфликт → пост уже есть, пропускаем (точная дедупликация)
    4. Обновляет sources.last_collected_at
    5. Пишет event: {type: "collector_run", source_id, new_posts_count}
    6. При ошибке: пишет sources.last_error + event: {type: "collector_error"}

ЭТАП 2: ML-ОБРАБОТКА
═══════════════════════════════════════════════════════════════
  ML Worker (poll loop или triggered после сбора):
    1. SELECT * FROM raw_posts WHERE ml_processed = false LIMIT 100

    2. Для каждого поста — keyword pre-filter:
       ── Проверяет text на наличие project.keywords
       ── Если ни одного keyword нет → relevance_label="irrelevant", score=0.0
       ── Проверяет project.exclude_keywords → отсекает мусор
       ── Проверяет project.risk_words → has_risk_words=true/false

    3. Relevance model (для тех, кто прошёл pre-filter):
       ── Input:  text
       ── Output: relevance_label ("relevant"/"irrelevant"), relevance_score (0..1)

    4. Sentiment model (для всех relevant):
       ── Input:  text
       ── Output: sentiment_label ("positive"/"neutral"/"negative"), sentiment_score (-1..1)

    5. Embedding model:
       ── Input:  text
       ── Output: vector(384)

    6. Семантическая дедупликация:
       ── SELECT id, dedup_group_id, embedding <=> {vec} AS dist
          FROM mentions
          WHERE project_id = {pid}
            AND published_at > now() - interval '3 days'
          ORDER BY embedding <=> {vec}
          LIMIT 5
       ── Если dist < 0.15 (cosine similarity > 0.85):
            → is_primary = false
            → dedup_group_id = existing group (или создать новую)
       ── Иначе:
            → is_primary = true
            → dedup_group_id = NULL

    7. INSERT INTO mentions (...все ML-поля...)
    8. UPDATE raw_posts SET ml_processed = true WHERE id IN (...)

    9. Пишет event: {type: "ml_processed", batch_size, relevant_count, dedup_count}

ЭТАП 3: СИНХРОНИЗАЦИЯ В CLICKHOUSE
═══════════════════════════════════════════════════════════════
  Сразу после шага 7:
    INSERT INTO mention_events (денормализованная строка из PG)
    ── Это append-only, без UPDATE

ЭТАП 4: SPIKE DETECTION
═══════════════════════════════════════════════════════════════
  Spike Worker (каждые 5 мин):
    1. Запрос к CH: count негативных за 30 мин vs baseline (см. выше)
    2. Если spike:
       ── Проверяет cooldown: SELECT * FROM alerts WHERE project_id=...
            AND cooldown_until > now()
       ── Если cooldown не истёк → пропуск
       ── Иначе:
            INSERT INTO alerts (...)  с cooldown_until = now() + 1 hour
            Пишет event: {type: "spike_detected", alert_id}

ЭТАП 5: API ОТДАЁТ ДАННЫЕ НА UI
═══════════════════════════════════════════════════════════════
  GET /mentions → PG запрос:
    SELECT m.*, rp.url, rp.title, rp.text, rp.author, rp.published_at, s.source_type
    FROM mentions m
    JOIN raw_posts rp ON m.raw_post_id = rp.id
    JOIN sources s ON rp.source_id = s.id
    WHERE m.project_id = {pid}
      AND m.is_primary = true               -- только уникальные
      AND m.relevance_label = 'relevant'    -- только релевантные
      [AND m.sentiment_label = {filter}]    -- опциональный фильтр
      [AND m.has_risk_words = true]         -- опциональный фильтр
    ORDER BY rp.published_at DESC
    LIMIT 50 OFFSET ...

  GET /mentions/{id}/duplicates → PG:
    SELECT m.*, rp.url, rp.title, rp.author, s.source_type
    FROM mentions m
    JOIN raw_posts rp ON m.raw_post_id = rp.id
    JOIN sources s ON rp.source_id = s.id
    WHERE m.dedup_group_id = {group_id}
      AND m.id != {mention_id}

  GET /analytics → ClickHouse запросы (см. примеры выше)

  GET /health → проверка:
    ── PG: SELECT 1
    ── CH: SELECT 1
    ── Collectors: SELECT source_id, last_error, last_collected_at FROM sources
         WHERE last_collected_at < now() - interval '10 min' → UNHEALTHY
    ── ML: SELECT count(*) FROM raw_posts WHERE ml_processed = false
         → если > 1000 → отставание, WARNING
```

---

## 5. Карточка mention на UI (что показываем)

```
┌─────────────────────────────────────────────────────────┐
│ [telegram] @banksta                    14 мар 2026 15:32│
│                                                         │
│ "Сбербанк сообщил о сбое в мобильном приложении..."     │
│                                                         │
│ ┌─────────────┐ ┌───────────────┐ ┌───────────────────┐ │
│ │ 🔴 negative │ │ relevance 0.94│ │ ⚠️ risk: "сбой"  │ │
│ │ score: -0.87│ │               │ │                   │ │
│ └─────────────┘ └───────────────┘ └───────────────────┘ │
│                                                         │
│ Ещё 4 источника ▸  (VK @bank_news, Telegram @finbase..)│
│                                                         │
│ [Открыть оригинал]                                      │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Парсеры (Collector Layer)

### Единый интерфейс

```python
class BaseCollector(ABC):
    @abstractmethod
    async def collect(self, source: Source) -> list[RawPost]:
        """Собрать новые посты с источника"""

    async def run(self, source: Source, db: AsyncSession):
        try:
            posts = await self.collect(source)
            saved = await self._save_posts(posts, source, db)
            source.last_collected_at = datetime.utcnow()
            source.last_error = None
            await log_event("collector_run", {"source_id": source.id, "new": saved})
        except Exception as e:
            source.last_error = str(e)
            await log_event("collector_error", {"source_id": source.id, "error": str(e)})

    async def _save_posts(self, posts, source, db) -> int:
        count = 0
        for p in posts:
            # ON CONFLICT DO NOTHING → точная дедупликация
            result = await db.execute(
                insert(RawPost).values(...).on_conflict_do_nothing(
                    index_elements=["source_id", "external_id"]
                )
            )
            count += result.rowcount
        return count
```

### Источники

| Источник | Подход | Что берём |
|----------|--------|-----------|
| **Telegram** | `httpx` GET `t.me/s/{channel}` → парсим HTML (не нужен API ключ для публичных) | text, date, views |
| **VK** | `httpx` → VK API `wall.get` (нужен service token) | text, date, likes, reposts |
| **RSS** | `feedparser.parse(url)` | title, description, link, pubDate |

---

## 7. ML Pipeline — модели

| Задача | Модель | Размер | Вход → Выход |
|--------|--------|--------|-------------|
| Relevance | fine-tuned classifier на ваших датасетах (или ruBERT + keywords) | ~400MB | text → {label, score} |
| Sentiment | `blanchefort/rubert-base-cased-sentiment` (pretrained) или fine-tune | ~400MB | text → {label, score} |
| Embedding | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | ~400MB | text → float[384] |

Можно все три заменить одной моделью (ruBERT-base) с двумя головами (relevance + sentiment) + CLS-токен как embedding. Это ускорит inference в 3 раза.

---

## 8. Структура проекта

```
brand-radar/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI + startup (запуск воркеров)
│   │   ├── config.py            # настройки из env
│   │   ├── db/
│   │   │   ├── postgres.py      # async engine, session
│   │   │   ├── clickhouse.py    # CH client
│   │   │   ├── models.py        # SQLAlchemy models (все таблицы PG)
│   │   │   └── migrations/      # alembic
│   │   ├── collectors/
│   │   │   ├── base.py          # BaseCollector
│   │   │   ├── telegram.py
│   │   │   ├── vk.py
│   │   │   └── rss.py
│   │   ├── ml/
│   │   │   ├── pipeline.py      # оркестрация: raw_post → mention
│   │   │   ├── relevance.py     # модель релевантности
│   │   │   ├── sentiment.py     # модель тональности
│   │   │   ├── embeddings.py    # sentence-transformers
│   │   │   └── dedup.py         # pgvector поиск + группировка
│   │   ├── workers/
│   │   │   ├── collector_worker.py  # loop: для каждого source → collect
│   │   │   ├── ml_worker.py         # loop: берёт raw_posts → ML → mentions
│   │   │   └── spike_worker.py      # loop: CH запрос → alerts
│   │   ├── services/
│   │   │   ├── mentions.py      # бизнес-логика ленты
│   │   │   ├── alerts.py
│   │   │   └── events.py
│   │   └── api/
│   │       ├── projects.py
│   │       ├── sources.py
│   │       ├── mentions.py
│   │       ├── alerts.py
│   │       ├── analytics.py     # проксирует в CH
│   │       └── health.py
│   ├── requirements.txt
│   └── Dockerfile
├── ml/
│   ├── train/                   # скрипты обучения на датасетах
│   ├── evaluate/                # метрики
│   └── models/                  # сохранённые веса
├── frontend/
├── docker-compose.yml           # PG+pgvector, ClickHouse, backend
└── README.md
```

---

## 9. Технологии

| Слой | Технология |
|------|-----------|
| Backend | Python 3.11+, FastAPI, asyncio |
| DB access | SQLAlchemy 2.0 + asyncpg (PG), clickhouse-driver (CH) |
| ML inference | transformers, sentence-transformers, torch |
| ML train | ваши датасеты + transformers Trainer |
| Парсинг | httpx, feedparser, beautifulsoup4 |
| PostgreSQL | 16 + pgvector extension |
| ClickHouse | latest, для аналитики и spike |
| Workers | asyncio tasks внутри FastAPI (lifespan) |
| Frontend | на выбор команды |

---

## 10. API контракты (FastAPI — request/response)

Все ответы обёрнуты в единый формат:
```json
{ "data": ..., "meta": { "total": 100, "page": 1, "page_size": 50 } }
```
Ошибки:
```json
{ "error": { "code": "NOT_FOUND", "message": "Project not found" } }
```

---

### 10.1 Projects (бренды)

#### `POST /api/projects` — создать проект

```
Request:
{
  "name": "Сбербанк",
  "keywords": ["сбербанк", "sberbank", "сбер"],
  "exclude_keywords": ["сберкнижка"],
  "risk_words": ["утечка", "мошенники", "сбой", "взлом"]
}

Response 201:
{
  "data": {
    "id": 1,
    "name": "Сбербанк",
    "keywords": ["сбербанк", "sberbank", "сбер"],
    "exclude_keywords": ["сберкнижка"],
    "risk_words": ["утечка", "мошенники", "сбой", "взлом"],
    "created_at": "2026-03-14T10:00:00Z"
  }
}
```

#### `GET /api/projects` — список проектов

```
Response 200:
{
  "data": [
    {
      "id": 1,
      "name": "Сбербанк",
      "keywords": ["сбербанк", "sberbank", "сбер"],
      "sources_count": 5,
      "mentions_today": 142,
      "unread_alerts": 2,
      "created_at": "2026-03-14T10:00:00Z"
    }
  ]
}
```

#### `GET /api/projects/{id}` — детали проекта

```
Response 200:
{
  "data": {
    "id": 1,
    "name": "Сбербанк",
    "keywords": [...],
    "exclude_keywords": [...],
    "risk_words": [...],
    "stats": {
      "total_mentions": 1520,
      "mentions_today": 142,
      "negative_today": 18,
      "active_sources": 5,
      "unread_alerts": 2
    },
    "created_at": "2026-03-14T10:00:00Z"
  }
}
```

#### `PUT /api/projects/{id}` — обновить настройки бренда

```
Request:
{
  "keywords": ["сбербанк", "sberbank", "сбер", "sber"],
  "risk_words": ["утечка", "мошенники", "сбой", "взлом", "штраф"]
}

Response 200: { "data": { ...обновлённый project } }
```

---

### 10.2 Sources (источники)

#### `POST /api/projects/{project_id}/sources` — добавить источник

```
Request:
{
  "source_type": "telegram",
  "source_config": {
    "channel": "banksta"
  },
  "poll_interval_s": 300
}

Response 201:
{
  "data": {
    "id": 1,
    "project_id": 1,
    "source_type": "telegram",
    "source_config": { "channel": "banksta" },
    "is_active": true,
    "poll_interval_s": 300,
    "last_collected_at": null,
    "last_error": null,
    "created_at": "2026-03-14T10:05:00Z"
  }
}
```

Примеры `source_config` для разных типов:
```json
// telegram
{ "channel": "banksta" }

// vk
{ "group_id": -12345, "domain": "bank_news" }

// rss
{ "feed_url": "https://example.com/rss" }
```

#### `GET /api/projects/{project_id}/sources` — список источников

```
Response 200:
{
  "data": [
    {
      "id": 1,
      "source_type": "telegram",
      "source_config": { "channel": "banksta" },
      "is_active": true,
      "poll_interval_s": 300,
      "last_collected_at": "2026-03-14T15:30:00Z",
      "last_error": null,
      "posts_collected": 847
    }
  ]
}
```

#### `DELETE /api/projects/{project_id}/sources/{id}` — удалить источник

```
Response 204 (no content)
```

---

### 10.3 Collector (управление сбором)

#### `POST /api/projects/{project_id}/collect` — запустить сбор вручную

```
Request (опционально):
{
  "source_ids": [1, 3]      // конкретные источники; если пусто — все
}

Response 202:
{
  "data": {
    "status": "started",
    "sources_triggered": 2
  }
}
```

#### `GET /api/projects/{project_id}/collector/status` — статус сборщиков

```
Response 200:
{
  "data": {
    "sources": [
      {
        "id": 1,
        "source_type": "telegram",
        "channel": "banksta",
        "status": "ok",                         // "ok" | "error" | "stale"
        "last_collected_at": "2026-03-14T15:30:00Z",
        "last_error": null,
        "posts_last_run": 3
      },
      {
        "id": 2,
        "source_type": "vk",
        "status": "error",
        "last_error": "VK API rate limit exceeded",
        "last_collected_at": "2026-03-14T14:00:00Z"
      }
    ],
    "ml_queue_size": 12       // raw_posts с ml_processed=false
  }
}
```

---

### 10.4 Mentions (лента)

#### `GET /api/projects/{project_id}/mentions` — лента упоминаний

```
Query params:
  ?sentiment=negative              // фильтр по тональности
  &relevance_min=0.5               // минимальный relevance_score
  &has_risk_words=true             // только с risk-словами
  &source_type=telegram            // фильтр по типу источника
  &date_from=2026-03-13            // с какой даты
  &date_to=2026-03-14              // по какую дату
  &search=сбой приложения          // полнотекстовый поиск
  &sort=published_at               // сортировка: published_at | relevance_score | sentiment_score
  &order=desc
  &page=1
  &page_size=50

Response 200:
{
  "data": [
    {
      "id": 1042,
      "source": {
        "type": "telegram",
        "name": "@banksta",
        "url": "https://t.me/banksta/12345"
      },
      "title": null,
      "text": "Сбербанк сообщил о масштабном сбое в мобильном приложении...",
      "author": "banksta",
      "published_at": "2026-03-14T15:32:00Z",

      "ml": {
        "relevance": { "label": "relevant", "score": 0.94 },
        "sentiment": { "label": "negative", "score": -0.87 },
        "risk_words_found": ["сбой"]
      },

      "dedup": {
        "group_id": 58,
        "is_primary": true,
        "duplicates_count": 4
      }
    }
  ],
  "meta": {
    "total": 342,
    "page": 1,
    "page_size": 50
  }
}
```

#### `GET /api/mentions/{id}` — карточка одного mention

```
Response 200:
{
  "data": {
    "id": 1042,
    "source": {
      "id": 1,
      "type": "telegram",
      "name": "@banksta",
      "url": "https://t.me/banksta/12345"
    },
    "title": null,
    "text": "Сбербанк сообщил о масштабном сбое в мобильном приложении. Пользователи не могут совершать переводы уже более двух часов.",
    "author": "banksta",
    "published_at": "2026-03-14T15:32:00Z",
    "collected_at": "2026-03-14T15:33:12Z",

    "ml": {
      "relevance": { "label": "relevant", "score": 0.94 },
      "sentiment": { "label": "negative", "score": -0.87 },
      "risk_words_found": ["сбой"],
      "processed_at": "2026-03-14T15:33:15Z"
    },

    "dedup": {
      "group_id": 58,
      "is_primary": true,
      "duplicates_count": 4,
      "duplicates": [
        {
          "id": 1045,
          "source_type": "vk",
          "source_name": "Банковские новости",
          "url": "https://vk.com/wall-12345_678",
          "published_at": "2026-03-14T15:35:00Z",
          "similarity": 0.92
        },
        {
          "id": 1048,
          "source_type": "telegram",
          "source_name": "@finbase",
          "url": "https://t.me/finbase/9876",
          "published_at": "2026-03-14T15:40:00Z",
          "similarity": 0.89
        }
      ]
    },

    "raw_meta": {
      "views": 45200,
      "forwards": 120
    }
  }
}
```

---

### 10.5 Alerts (алерты)

#### `GET /api/projects/{project_id}/alerts` — список алертов

```
Query params:
  ?is_read=false
  &page=1

Response 200:
{
  "data": [
    {
      "id": 5,
      "alert_type": "negative_spike",
      "severity": "high",
      "title": "Всплеск негатива: 47 упоминаний за 30 мин (норма: 8)",
      "message": "Обнаружен рост негативных упоминаний в 5.9x от baseline. Основная тема: сбой мобильного приложения.",
      "mention_ids": [1042, 1045, 1048, 1051],
      "triggered_at": "2026-03-14T15:45:00Z",
      "cooldown_until": "2026-03-14T16:45:00Z",
      "is_read": false
    }
  ]
}
```

#### `PATCH /api/alerts/{id}` — пометить прочитанным

```
Request:
{ "is_read": true }

Response 200: { "data": { ...updated alert } }
```

---

### 10.6 Analytics (аналитика — данные из ClickHouse)

#### `GET /api/projects/{project_id}/analytics/sentiment-timeline`

```
Query params:
  ?period=30d                     // 7d | 30d | 90d
  &granularity=day                // hour | day

Response 200:
{
  "data": [
    { "date": "2026-03-01", "positive": 45, "neutral": 120, "negative": 12 },
    { "date": "2026-03-02", "positive": 38, "neutral": 115, "negative": 15 },
    ...
  ]
}
```

#### `GET /api/projects/{project_id}/analytics/volume`

```
Query params:
  ?period=48h
  &granularity=hour

Response 200:
{
  "data": [
    {
      "hour": "2026-03-14T10:00:00Z",
      "total": 24,
      "negative": 3,
      "with_risk_words": 1
    },
    ...
  ]
}
```

#### `GET /api/projects/{project_id}/analytics/top-sources`

```
Query params:
  ?period=7d
  &sentiment=negative

Response 200:
{
  "data": [
    {
      "source_type": "telegram",
      "source_id": 1,
      "source_name": "@banksta",
      "count": 42,
      "avg_sentiment": -0.65
    },
    ...
  ]
}
```

---

### 10.7 Events (журнал событий)

#### `GET /api/events`

```
Query params:
  ?project_id=1
  &event_type=collector_error      // фильтр по типу
  &page=1

Response 200:
{
  "data": [
    {
      "id": 892,
      "project_id": 1,
      "event_type": "spike_detected",
      "payload": {
        "alert_id": 5,
        "current_count": 47,
        "baseline_count": 8,
        "multiplier": 5.9
      },
      "created_at": "2026-03-14T15:45:00Z"
    },
    {
      "id": 891,
      "event_type": "ml_processed",
      "payload": {
        "batch_size": 100,
        "relevant_count": 67,
        "irrelevant_count": 33,
        "dedup_count": 12
      },
      "created_at": "2026-03-14T15:33:15Z"
    },
    {
      "id": 890,
      "event_type": "collector_error",
      "payload": {
        "source_id": 2,
        "source_type": "vk",
        "error": "VK API rate limit exceeded"
      },
      "created_at": "2026-03-14T14:00:05Z"
    }
  ]
}
```

Типы событий:
- `collector_run` — успешный сбор
- `collector_error` — ошибка сбора
- `ml_processed` — ML обработал батч
- `spike_detected` — обнаружен всплеск
- `alert_sent` — алерт отправлен
- `source_added` / `source_removed`
- `project_created` / `project_updated`

---

### 10.8 Health

#### `GET /api/health`

```
Response 200:
{
  "status": "degraded",           // "healthy" | "degraded" | "unhealthy"
  "components": {
    "postgres": { "status": "healthy", "latency_ms": 2 },
    "clickhouse": { "status": "healthy", "latency_ms": 5 },
    "collectors": {
      "status": "degraded",
      "healthy": 4,
      "unhealthy": 1,
      "details": [
        {
          "source_id": 2,
          "source_type": "vk",
          "status": "error",
          "last_error": "VK API rate limit exceeded",
          "last_success": "2026-03-14T14:00:00Z"
        }
      ]
    },
    "ml_pipeline": {
      "status": "healthy",
      "queue_size": 12,            // необработанных raw_posts
      "avg_processing_time_ms": 150
    }
  },
  "timestamp": "2026-03-14T15:50:00Z"
}
```

---

## 11. E2E: порядок реализации

```
1. docker-compose (PG + pgvector + CH)
2. DB models + миграции (alembic)
3. Один парсер (Telegram публичные каналы)
4. ML pipeline (relevance → sentiment → embedding → dedup)
5. Sync в CH
6. API: mentions с фильтрами
7. UI: лента с карточками
8. Spike detection + alerts
9. Health + events
──── E2E готов ────
10. Остальные парсеры (VK, RSS)
11. Аналитика (графики из CH)
12. Polish UI, метрики ML
```
