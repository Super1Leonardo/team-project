import type { PageServerLoad } from './$types';
import { mockClusters } from '$lib/server/mockData';

export const load: PageServerLoad = async () => {
	return {
		clusters: mockClusters
	};
};