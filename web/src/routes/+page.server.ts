import type { PageServerLoad } from './$types';
import { api } from '$lib/api/client';

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';

export const load: PageServerLoad = async ({ url }) => {
	let mentions: any[] = [];
	let error: string | undefined;

	const confidence = url.searchParams.get('confidence');
	const period = url.searchParams.get('period');
	const sentiment = url.searchParams.get('sentiment');

	const queryParams = new URLSearchParams();
	queryParams.set('limit', '50');

	if (confidence) queryParams.set('confidence', confidence);
	if (period) queryParams.set('period', period);
	if (sentiment) queryParams.set('sentiment', sentiment);

	const mentionsRes = await api.get<any[]>(
		`${API_BASE_URL}/api/feed?${queryParams.toString()}`
	);

	if (mentionsRes.error) {
		error = mentionsRes.error.message;
	} else if (mentionsRes.data) {
		mentions = mentionsRes.data;
	}

	return {
		mentions,
		error: error ? { message: error } : undefined,
	};
};
