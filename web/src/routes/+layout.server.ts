import type { PageServerLoad } from './$types';
import { mockSources } from '$lib/server/sources';

let sources = [...mockSources];

export const load: PageServerLoad = async () => {
	const errorCount = sources.filter(s => s.is_active && s.last_error !== null).length;

	return {
		sources,
		errorCount
	};
};
