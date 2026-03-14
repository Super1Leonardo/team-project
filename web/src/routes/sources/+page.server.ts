import type { Actions, PageServerLoad } from "./$types";
import { mockSources, type Source } from "$lib/server/sources";

let sources: Source[] = [...mockSources];

export const load: PageServerLoad = async () => {
  return {
    sources,
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
