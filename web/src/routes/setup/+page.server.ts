import type { Actions, PageServerLoad } from './$types';

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
	created_at: string;
}

async function getOrCreateProject(): Promise<Project | null> {
	const projects = await fetchJson<Project[]>(`${API_BASE_URL}/api/projects`);
	if (!projects || projects.length === 0) {
		const newProject = await fetchJson<Project>(`${API_BASE_URL}/api/projects`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ name: "Мой проект", keywords: ["сбербанк", "sberbank", "сбер"], exclude_keywords: [], risk_words: [] })
		});
		return newProject;
	}
	return projects[0];
}

export const load: PageServerLoad = async () => {
	const project = await getOrCreateProject();

	return {
		project
	};
};

export const actions: Actions = {
	updateProject: async ({ request }) => {
		const data = await request.formData();

		const projectId = parseInt(data.get('project_id') as string);
		const keywordsStr = data.get('keywords') as string;
		const excludeKeywordsStr = data.get('exclude_keywords') as string;
		const riskWordsStr = data.get('risk_words') as string;

		const keywords = keywordsStr.split(',').map(k => k.trim()).filter(k => k);
		const exclude_keywords = excludeKeywordsStr.split(',').map(k => k.trim()).filter(k => k);
		const risk_words = riskWordsStr.split(',').map(k => k.trim()).filter(k => k);

		const result = await fetchJson<Project>(
			`${API_BASE_URL}/api/projects/${projectId}`,
			{
				method: "PATCH",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ keywords, exclude_keywords, risk_words })
			}
		);

		if (!result) {
			return { success: false, error: "Failed to update project" };
		}

		return { success: true, message: 'Настройки сохранены', project: result };
	}
};
