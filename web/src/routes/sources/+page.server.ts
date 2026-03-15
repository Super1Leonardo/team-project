import type { Actions, PageServerLoad } from "./$types";
import { mockSources, type Source } from "$lib/server/sources";

let sources: Source[] = [...mockSources];

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';

async function fetchHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    if (!response.ok) return null;
    return await response.json();
  } catch (err) {
    console.log(err);
    return null;
  }
}

export const load: PageServerLoad = async () => {
  const health = await fetchHealth();

  return {
    sources,
    health,
  };
};

export const actions: Actions = {
  toggleSource: async ({ request }) => {
    const data = await request.formData();
    const sourceId = parseInt(data.get("source_id") as string);

    sources = sources.map((s) =>
      s.id === sourceId ? { ...s, is_active: !s.is_active } : s
    );

    return { success: true };
  },
};
