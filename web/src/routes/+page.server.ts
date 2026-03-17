import type { PageServerLoad } from './$types';
import { api } from '$lib/api/client';
import type { MentionCluster } from '$lib/types/brandradar';

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';

export const load: PageServerLoad = async ({ url }) => {
	let clusters: MentionCluster[] = [];
	let error: string | undefined;
	let pagination: { total: number; page: number; pageSize: number } | undefined;

	const page = parseInt(url.searchParams.get('page') || '1');
	const perPage = parseInt(url.searchParams.get('per_page') || '20');
	const confidence = url.searchParams.get('confidence');
	const period = url.searchParams.get('period');
	const sentiment = url.searchParams.get('sentiment');
	const riskWordsOnly = url.searchParams.get('risk_words_only') === 'true';

	const queryParams = new URLSearchParams();
	queryParams.set('page', String(page));
	queryParams.set('page_size', String(perPage));

	if (confidence) queryParams.set('confidence', confidence);
	if (period) queryParams.set('period', period);
	if (sentiment) queryParams.set('sentiment', sentiment);
	if (riskWordsOnly) queryParams.set('risk_words_only', 'true');

	const clustersRes = await api.get<MentionCluster[]>(
		`${API_BASE_URL}/api/feed/clusters?${queryParams.toString()}`
	);

	if (clustersRes.error) {
		error = clustersRes.error.message;
	} else if (clustersRes.data) {
		clusters = clustersRes.data;
		if (clustersRes.meta) {
			pagination = {
				total: clustersRes.meta.total || 0,
				page: clustersRes.meta.page || 1,
				pageSize: clustersRes.meta.page_size || perPage
			};
		}
	}

	return {
		clusters,
		pagination,
		error: error ? { message: error } : undefined,
	};
};
