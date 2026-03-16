import type { PageServerLoad } from "./$types";

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL ||
  "http://localhost:8000";

async function fetchJson<T>(
  url: string,
  options?: RequestInit,
): Promise<T | null> {
  try {
    const response = await fetch(url, options);
    if (!response.ok) return null;
    const data = await response.json();
    return data.data ?? data;
  } catch {
    return null;
  }
}

interface Project {
  id: number;
}

async function getOrCreateProject(): Promise<Project | null> {
  const projects = await fetchJson<Project[]>(`${API_BASE_URL}/api/projects`);
  if (!projects || projects.length === 0) {
    return await fetchJson<Project>(`${API_BASE_URL}/api/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "Мой проект",
        keywords: ["сбербанк", "sberbank", "сбер"],
        exclude_keywords: [],
        risk_words: [],
      }),
    });
  }
  return projects[0];
}

export const load: PageServerLoad = async ({ url }) => {
  const project = await getOrCreateProject();

  let timeline: any[] = [];
  let kpi = { total: 0, avgMlScore: "0.0", spikeAlerts: 0 };

  if (project) {
    // 1. Берем фильтры из URL (как в ленте)
    const confidence = url.searchParams.get('confidence') || '0.7';
    const period = url.searchParams.get('period') || '7d';

    const queryParams = new URLSearchParams({
      limit: '500', // Для графика нужно больше данных
      confidence,
      period
    });

    // 2. Запрашиваем уже отфильтрованные данные
    const response = await fetchJson<any[]>(
      `${API_BASE_URL}/api/projects/${project.id}/mentions?${queryParams.toString()}`
    );
    const mentions = Array.isArray(response) ? response : [];

    kpi.total = mentions.length;

    let totalScore = 0;
    const daysMap: Record<string, any> = {};

    // 3. Агрегируем метрики
    mentions.forEach((m) => {
      // Поддерживаем оба формата (на случай если FastAPI возвращает relevance_score)
      const score = m.relevance_score ?? m.ml_confidence ?? 0;
      totalScore += score;

      const dateStr = new Date(m.published_at || m.publishedAt).toISOString().split("T")[0];
      if (!daysMap[dateStr]) {
        daysMap[dateStr] = { date: dateStr, positive: 0, negative: 0, neutral: 0, mlConfidenceSum: 0, count: 0 };
      }

      const sentiment = m.sentiment_label ?? m.sentiment ?? 'neutral';
      if (sentiment === "positive") daysMap[dateStr].positive++;
      else if (sentiment === "negative") daysMap[dateStr].negative++;
      else daysMap[dateStr].neutral++;

      daysMap[dateStr].mlConfidenceSum += score;
      daysMap[dateStr].count++;
    });

    kpi.avgMlScore = mentions.length > 0
      ? ((totalScore / mentions.length) * 100).toFixed(1)
      : "0.0";

    // Собираем график
    timeline = Object.values(daysMap).map((d) => ({
      date: d.date,
      positive: d.positive,
      negative: d.negative,
      neutral: d.neutral,
      mlConfidence: d.count > 0 ? d.mlConfidenceSum / d.count : 0,
    })).sort((a, b) => a.date.localeCompare(b.date));
  }

  return { timeline, kpi };
};