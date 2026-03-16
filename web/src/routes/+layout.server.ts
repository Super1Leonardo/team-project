import type { PageServerLoad } from './$types';
import { api } from '$lib/api/client';

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';

export const load: PageServerLoad = async () => {
	const healthRes = await api.get<{
		status: string;
		postgres: string;
		clickhouse: string;
		ml: string;
		ml_url: string;
		ml_error: string | null;
		ml_queue_size: number;
	}>(`${API_BASE_URL}/api/health`);

	return {
		health: healthRes.data ?? null,
		healthError: healthRes.error?.message,
	};
};
