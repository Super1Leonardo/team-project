import type { PageServerLoad } from './$types';
import { mockSources } from '$lib/server/sources';

let sources = [...mockSources];

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';

async function fetchHealth() {
	try {
		const response = await fetch(`${API_BASE_URL}/api/health`);
		if (!response.ok) return null;
		return await response.json();
	} catch {
		return null;
	}
}

export const load: PageServerLoad = async () => {
	const errorCount = sources.filter(s => s.is_active && s.last_error !== null).length;
	const health = await fetchHealth();

	return {
		sources,
		errorCount,
		health
	};
};
