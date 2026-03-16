import type { PageServerLoad } from './$types';
import { api } from '$lib/api/client';

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';

interface Project {
	id: number;
	name: string;
	keywords: string[];
	exclude_keywords: string[];
	risk_words: string[];
}

async function getOrCreateProject(): Promise<{ project: Project | null; error?: string }> {
	const projectsRes = await api.get<Project[]>(`${API_BASE_URL}/api/projects`);

	if (projectsRes.error) {
		return { project: null, error: projectsRes.error.message };
	}

	if (!projectsRes.data || projectsRes.data.length === 0) {
		const createRes = await api.post<Project>(`${API_BASE_URL}/api/projects`, {
			name: 'Мой проект',
			keywords: ['сбербанк', 'sberbank', 'сбер'],
			exclude_keywords: [],
			risk_words: [],
		});

		if (createRes.error) {
			return { project: null, error: createRes.error.message };
		}

		return { project: createRes.data ?? null };
	}

	return { project: projectsRes.data[0] };
}

export const load: PageServerLoad = async ({ url }) => {
	const mockState = url.searchParams.get('__mock');
	if (mockState === 'success') {
		return {
			mentions: [{
				id: 1,
				raw_post_id: 1,
				project_id: 1,
				source_id: 1,
				source_type: 'telegram',
				source_name: 'telegram',
				url: 'https://t.me/durov/101',
				title: 'Сбой приложения',
				text: 'Тестовый сбой в системе',
				author: 'Test Author',
				published_at: new Date().toISOString(),
				relevance_score: 1.0,
				relevance_label: 'relevant',
				sentiment_score: 0.2,
				sentiment_label: 'negative',
				has_risk_words: true,
				dedup_group_id: null,
				is_primary: true
			}],
			error: undefined
		};
	}
	if (mockState === 'error') {
		return { mentions: [], error: { message: 'ML API недоступен' } };
	}
	const { project, error: projectError } = await getOrCreateProject();

	let mentions: any[] = [];
	let error: string | undefined;

	if (projectError) {
		error = projectError;
	} else if (project) {
		const confidence = url.searchParams.get('confidence');
		const period = url.searchParams.get('period');
		const sentiment = url.searchParams.get('sentiment');

		const queryParams = new URLSearchParams();
		queryParams.set('limit', '50');

		if (confidence) queryParams.set('confidence', confidence);
		if (period) queryParams.set('period', period);
		if (sentiment) queryParams.set('sentiment', sentiment);

		const mentionsRes = await api.get<any[]>(
			`${API_BASE_URL}/api/projects/${project.id}/mentions?${queryParams.toString()}`
		);

		if (mentionsRes.error) {
			error = mentionsRes.error.message;
		} else if (mentionsRes.data) {
			mentions = mentionsRes.data;
		}
	}

	return {
		mentions,
		error: error ? { message: error } : undefined,
	};
};
