import type { Actions, PageServerLoad } from './$types';
import { fail } from '@sveltejs/kit';
import { api } from '$lib/api/client';

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';

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

interface CollectorStatus {
	ml_queue_size: number;
	raw_posts_total: number;
	raw_posts_processed: number;
	raw_posts_pending: number;
	raw_posts_failed: number;
	processing_status: 'idle' | 'processing' | 'ready';
	sources: Source[];
}

async function getOrCreateProject(): Promise<{ project: Project | null; error?: string }> {
	const projectsRes = await api.get<Project[]>(`${API_BASE_URL}/api/projects`);

	if (projectsRes.error) {
		return { project: null, error: projectsRes.error.message };
	}

	if (!projectsRes.data || projectsRes.data.length === 0) {
		const createRes = await api.post<Project>(`${API_BASE_URL}/api/projects`, {
			name: 'Мой проект',
			keywords: [],
			exclude_keywords: [],
		});

		if (createRes.error) {
			return { project: null, error: createRes.error.message };
		}

		return { project: createRes.data ?? null };
	}

	return { project: projectsRes.data[0] };
}

async function fetchHealth() {
	const healthRes = await api.get<{
		status: string;
		postgres: string;
		clickhouse: string;
		ml: string;
		ml_url: string;
		ml_error: string | null;
		ml_queue_size: number;
	}>(`${API_BASE_URL}/api/health`);

	return healthRes.data ?? null;
}

async function fetchCollectorStatus(projectId: number) {
	const res = await api.get<CollectorStatus>(
		`${API_BASE_URL}/api/projects/${projectId}/collector/status`
	);
	return res.data ?? null;
}

export const load: PageServerLoad = async () => {
	const { project, error: projectError } = await getOrCreateProject();

	let sources: Source[] = [];
	let error: string | undefined;

	if (projectError) {
		error = projectError;
	} else if (project) {
		const sourcesRes = await api.get<Source[]>(
			`${API_BASE_URL}/api/projects/${project.id}/sources`
		);

		if (sourcesRes.error) {
			error = sourcesRes.error.message;
		} else {
			sources = sourcesRes.data ?? [];
		}
	}

	const health = await fetchHealth();

	const collector = project ? await fetchCollectorStatus(project.id) : null;

	return {
		project,
		sources,
		health,
		collector,
		error: error ? { message: error } : undefined,
	};
};

export const actions: Actions = {
	toggleSource: async ({ request }) => {
		const formData = await request.formData();
		const sourceId = parseInt(formData.get('source_id') as string);
		const projectId = parseInt(formData.get('project_id') as string);
		const currentState = formData.get('current_state') === 'true';

		const result = await api.patch<Source>(
			`${API_BASE_URL}/api/projects/${projectId}/sources/${sourceId}`,
			{ is_active: !currentState }
		);

		if (result.error) {
			return fail(400, { error: result.error.message });
		}

		return { success: true };
	},

	createSource: async ({ request }) => {
		const formData = await request.formData();
		const projectId = parseInt(formData.get('project_id') as string);
		const sourceType = formData.get('source_type') as string;
		const sourceConfigStr = formData.get('source_config') as string;
		const pollInterval = parseInt(formData.get('poll_interval') as string) || 3600;

		let sourceConfig: Record<string, unknown> = {};

		if (sourceType === 'telegram') {
			sourceConfig = { channel: sourceConfigStr };
		} else if (sourceType === 'rss') {
			sourceConfig = { url: sourceConfigStr };
		} else if (sourceType === 'website') {
			sourceConfig = { url: sourceConfigStr };
		}

		const result = await api.post<Source>(
			`${API_BASE_URL}/api/projects/${projectId}/sources`,
			{
				source_type: sourceType,
				source_config: sourceConfig,
				poll_interval_s: pollInterval,
				is_active: true
			}
		);

		if (result.error) {
			return fail(400, { error: result.error.message });
		}

		return { success: true };
	},

	deleteSource: async ({ request }) => {
		const formData = await request.formData();
		const sourceId = parseInt(formData.get('source_id') as string);
		const projectId = parseInt(formData.get('project_id') as string);

		const result = await api.delete<void>(
			`${API_BASE_URL}/api/projects/${projectId}/sources/${sourceId}`
		);

		if (result.error) {
			return fail(400, { error: result.error.message });
		}

		return { success: true };
	},
};
