import type { PageServerLoad } from './$types';

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T | null> {
	try {
		const response = await fetch(url, options);
		if (!response.ok) return null;
		const data = await response.json();
		return data.data ?? data; // SvelteKit ожидает данные, разворачиваем API-конверт
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
			body: JSON.stringify({ 
				name: "Мой проект", 
				keywords: ["сбербанк", "sberbank", "сбер"], 
				exclude_keywords: [], 
				risk_words: [] 
			})
		});
	}
	return projects[0];
}

export const load: PageServerLoad = async ({ url }) => {
	const project = await getOrCreateProject();
	let mentions: any[] = [];

	if (project) {
		// 1. Извлекаем параметры фильтрации из URL
		const confidence = url.searchParams.get('confidence');
		const period = url.searchParams.get('period');
		
		// 2. Формируем строку запроса (Query String)
		const queryParams = new URLSearchParams();
		queryParams.set('limit', '50'); // Дефолтный лимит
		
		// Если параметры есть в URL, прокидываем их в API
		if (confidence) queryParams.set('confidence', confidence);
		if (period) queryParams.set('period', period);

		// 3. Запрашиваем отфильтрованные данные из PostgreSQL через FastAPI
		const response = await fetchJson<any[]>(
			`${API_BASE_URL}/api/projects/${project.id}/mentions?${queryParams.toString()}`
		);
		
		if (Array.isArray(response)) {
			mentions = response;
		}
	}

	return {
		mentions
	};
};