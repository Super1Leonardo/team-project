import type { PageServerLoad } from './$types';
import { api } from '$lib/api/client';

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';

export const load: PageServerLoad = async ({ url }) => {
	let mentions: any[] = [];
	let error: string | undefined;
	let pagination: { total: number; page: number; pageSize: number } | undefined;

	const page = parseInt(url.searchParams.get('page') || '1');
	const perPage = parseInt(url.searchParams.get('per_page') || '50');
	const confidence = url.searchParams.get('confidence');
	const period = url.searchParams.get('period');
	const sentiment = url.searchParams.get('sentiment');

	const queryParams = new URLSearchParams();
	queryParams.set('page', String(page));
	queryParams.set('page_size', String(perPage));

	if (confidence) queryParams.set('confidence', confidence);
	if (period) queryParams.set('period', period);
	if (sentiment) queryParams.set('sentiment', sentiment);

	const mentionsRes = await api.get<unknown[]>(
		`${API_BASE_URL}/api/feed?${queryParams.toString()}`
	);

	if (mentionsRes.error) {
		error = mentionsRes.error.message;
	} else if (mentionsRes.data) {
		mentions = mentionsRes.data as any[];
		if (mentionsRes.meta) {
			pagination = {
				total: mentionsRes.meta.total || 0,
				page: mentionsRes.meta.page || 1,
				pageSize: mentionsRes.meta.page_size || perPage
			};
		}
	}

	return {
		mentions,
		pagination,
		error: error ? { message: error } : undefined,
	};
};
