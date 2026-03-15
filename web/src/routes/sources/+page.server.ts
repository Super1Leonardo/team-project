import type { Actions, PageServerLoad } from "./$types";

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

interface Source {
	id: number;
	project_id: number;
	source_type: string;
	source_config: Record<string, unknown>;
	is_active: boolean;
	poll_interval_s: number;
	last_collected_at: string | null;
	last_error: string | null;
	created_at: string;
	raw_posts_count: number | null;
}

async function getOrCreateProject(): Promise<Project | null> {
	const projects = await fetchJson<Project[]>(`${API_BASE_URL}/api/projects`);
	if (!projects || projects.length === 0) {
		const newProject = await fetchJson<Project>(`${API_BASE_URL}/api/projects`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ name: "Мой проект", keywords: [], exclude_keywords: [] })
		});
		return newProject;
	}
	return projects[0];
}

async function fetchHealth() {
	return fetchJson<{ status: string; postgres: string; clickhouse: string; ml_queue_size: number }>(`${API_BASE_URL}/api/health`);
}

export const load: PageServerLoad = async () => {
	const project = await getOrCreateProject();
	const sources = project ? await fetchJson<Source[]>(`${API_BASE_URL}/api/projects/${project.id}/sources`) ?? [] : [];
	const health = await fetchHealth();

	return {
		project,
		sources,
		health,
	};
};

export const actions: Actions = {
	toggleSource: async ({ request }) => {
		const data = await request.formData();
		const sourceId = parseInt(data.get("source_id") as string);
		const projectId = parseInt(data.get("project_id") as string);
		const currentState = data.get("current_state") === "true";

		const result = await fetchJson<Source>(
			`${API_BASE_URL}/api/projects/${projectId}/sources/${sourceId}`,
			{
				method: "PATCH",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !currentState })
			}
		);

		if (!result) {
			return { success: false, error: "Failed to update source" };
		}

		return { success: true };
	},
};
