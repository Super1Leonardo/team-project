# Deploy Guide

Этот проект деплоится через `GitLab CI/CD` на сервер по `SSH` и запускается через `docker compose`.

Важно:
- ветка `master` защищена
- напрямую пушить в `master` нельзя
- рабочий поток: `feature branch -> Merge Request -> merge в master -> production deploy`

## 1. Что должно быть на сервере

На сервере должны быть установлены:

```bash
docker --version
docker compose version
```

Нужен пользователь, под которым GitLab сможет зайти по `SSH`.

Пример целевой папки:

```bash
mkdir -p /opt/brandradar_jbtteam
```

## 2. Что нужно добавить в GitLab Variables

Откройте:

`GitLab -> Settings -> CI/CD -> Variables`

Добавьте переменные:

- `SSH_PRIVATE_KEY`
- `SSH_KNOWN_HOSTS`
- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_BASE_PATH`
- `DEPLOY_ENV_FILE` опционально

Рекомендуемые значения:

- `DEPLOY_HOST` = IP или домен сервера
- `DEPLOY_USER` = пользователь на сервере
- `DEPLOY_BASE_PATH` = `/opt/brandradar_jbtteam`

### SSH_PRIVATE_KEY

Это приватный ключ, которым GitLab runner будет подключаться к серверу.

Если ключа еще нет:

```bash
ssh-keygen -t ed25519 -C "gitlab-deploy"
```

Публичную часть добавьте на сервер в:

```bash
~/.ssh/authorized_keys
```

Р›СѓС‡С€Рµ С…СЂР°РЅРёС‚СЊ `SSH_PRIVATE_KEY` РєР°Рє GitLab `File` variable.
Р•СЃР»Рё РёСЃРїРѕР»СЊР·СѓРµС‚Рµ РѕР±С‹С‡РЅСѓСЋ text variable, РІСЃС‚Р°РІР»СЏР№С‚Рµ РїРѕР»РЅС‹Р№ РєР»СЋС‡ С†РµР»РёРєРѕРј СЃРѕ СЃС‚СЂРѕРєР°РјРё `BEGIN/END PRIVATE KEY`.
РљР»СЋС‡ РґРѕР»Р¶РµРЅ Р±С‹С‚СЊ Р±РµР· passphrase, РёРЅР°С‡Рµ CI РЅРµ СЃРјРѕР¶РµС‚ РґРѕР±Р°РІРёС‚СЊ РµРіРѕ РІ `ssh-agent`.

### SSH_KNOWN_HOSTS

Сгенерировать можно так:

```bash
ssh-keyscan -H <your-server-host>
```

Пример:

```bash
ssh-keyscan -H 203.0.113.10
```

### DEPLOY_ENV_FILE

Можно не использовать, если `.env` уже лежит на сервере в директории деплоя.

Если хотите, чтобы GitLab сам загружал `.env`, положите в эту переменную полный текст `.env`.

Пример:

```env
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_PHONE=+79991234567
POSTGRES_DB=brandradar
POSTGRES_USER=brandradar
POSTGRES_PASSWORD=brandradar
CLICKHOUSE_DATABASE=brandradar_ml
CLICKHOUSE_USER=brandradar
CLICKHOUSE_PASSWORD=brandradar
BACKEND_CORS_ORIGINS=http://your-frontend-domain
WEB_ORIGIN=http://your-frontend-domain
```

## 3. Как работать с новой веткой

Создать ветку:

```bash
git switch -c feature/deploy-guide
```

Проверить изменения:

```bash
git status
```

Закоммитить:

```bash
git add .
git commit -m "Add deploy guide"
```

Запушить ветку:

```bash
git push -u origin feature/deploy-guide
```

## 4. Как задеплоить branch на сервер через GitLab

После `push`:

1. Откройте `GitLab -> CI/CD -> Pipelines`
2. Найдите pipeline для вашей ветки
3. Нажмите manual job `deploy_branch`

Что произойдет:

- GitLab зайдет на сервер по `SSH`
- создаст папку:

```text
${DEPLOY_BASE_PATH}/${CI_COMMIT_REF_SLUG}
```

- скопирует туда проект
- зальет `.env`, если указан `DEPLOY_ENV_FILE`
- выполнит:

```bash
docker compose up -d --build --remove-orphans
```

Пример preview-пути для ветки `feature/deploy-guide`:

```text
/opt/brandradar_jbtteam/feature-deploy-guide
```

## 5. Как сделать Merge Request в master

Так как `master` protected, merge делается только через `Merge Request`.

После push ветки:

1. Откройте репозиторий в GitLab
2. Нажмите `Create merge request`
3. Source branch: ваша ветка
4. Target branch: `master`
5. Проверьте, что pipeline прошел
6. Нажмите `Merge`

Если GitLab показывает конфликты, сначала подтяните `master` локально и разрешите их:

```bash
git fetch origin
git switch feature/deploy-guide
git merge origin/master
```

После фикса конфликтов:

```bash
git add .
git commit
git push
```

## 6. Как задеплоить master в production

После merge в `master`:

1. Откройте pipeline ветки `master`
2. Нажмите manual job `deploy_production`

Он задеплоит проект в:

```text
${DEPLOY_BASE_PATH}/production
```

И выполнит:

```bash
docker compose up -d --build --remove-orphans
```

## 7. Полный сценарий от начала до конца

```bash
git switch -c feature/my-change
git add .
git commit -m "My change"
git push -u origin feature/my-change
```

Дальше в GitLab:

1. Запустить `deploy_branch`
2. Проверить preview на сервере
3. Создать `Merge Request` в `master`
4. Смёржить
5. Запустить `deploy_production`

## 8. Если нужно проверить руками на сервере

Зайти на сервер:

```bash
ssh <DEPLOY_USER>@<DEPLOY_HOST>
```

Перейти в production:

```bash
cd <DEPLOY_BASE_PATH>/production
```

Проверить контейнеры:

```bash
docker compose ps
docker compose logs -f python
docker compose logs -f web
```

Перезапустить вручную:

```bash
docker compose up -d --build --remove-orphans
```

## 9. Частые проблемы

### `Permission denied (publickey)`

Проблема в `SSH_PRIVATE_KEY` или в `authorized_keys` на сервере.

### `Host key verification failed`

Неверная переменная `SSH_KNOWN_HOSTS`.

### `DEPLOY_ENV_FILE is not set`

Это не ошибка.
Это значит, что pipeline оставит существующий `.env` на сервере как есть.

### `master` не пушится

Это нормально: ветка защищена.
Используйте:

- отдельную ветку
- `Merge Request`

## 10. Где лежит логика деплоя

- CI-конфиг: [`.gitlab-ci.yml`](./.gitlab-ci.yml)
- deploy-скрипт: [`scripts/deploy_remote.sh`](./scripts/deploy_remote.sh)
