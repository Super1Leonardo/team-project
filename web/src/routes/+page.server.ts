import type { PageServerLoad } from './$types';

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T | null> {
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
	name: string;
	keywords: string[];
	exclude_keywords: string[];
	risk_words: string[];
}

async function getOrCreateProject(): Promise<Project | null> {
	const projects = await fetchJson<Project[]>(`${API_BASE_URL}/api/projects`);
	if (!projects || projects.length === 0) {
		return await fetchJson<Project>(`${API_BASE_URL}/api/projects`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ name: "Мой проект", keywords: ["сбербанк", "sberbank", "сбер"], exclude_keywords: [], risk_words: [] })
		});
	}
	return projects[0];
}

export const load: PageServerLoad = async () => {
	const project = await getOrCreateProject();
	let clusters: any[] = [];

	if (project) {
		// Тянем реальные данные с бэкенда
		const response = await fetchJson<{items: any[]}>(`${API_BASE_URL}/api/projects/${project.id}/mentions?limit=50`);
		
		if (response && response.items) {
			// Мапим ответ API под интерфейс Cluster, который ожидает ArticleList.svelte
			clusters = response.items.map(m => ({
				id: String(m.id),
				title: m.title || m.author || 'Без заголовка',
				source: m.source_type,
				publishedAt: m.published_at,
				sentiment: m.sentiment_label || 'neutral',
				// Преобразуем 0.0-1.0 в проценты для отображения уверенности модели
				mlScore: Math.round((m.relevance_score || 0) * 100),
				riskWords: m.has_risk_words ? ['Внимание: слова риска'] : [],
				text: m.text || '',
				duplicates: [] // Пока дедупликация на бэке агрегирует группы, оставим пустым
			}));
		}
	}

	return {
		clusters
	};
};