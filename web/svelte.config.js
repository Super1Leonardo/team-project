import adapter from "@sveltejs/adapter-node";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: { 
    adapter: adapter(), 
    experimental: { remoteFunctions: true },
    csrf: {
      trustedOrigins: ['http://team-31-brandradar-d0e339.pages.prodcontest.ru']
    }
  },
  compilerOptions: { experimental: { async: true } },
  vitePlugin: {
    dynamicCompileOptions: ({ filename }) =>
      filename.includes("node_modules") ? undefined : { runes: true },
  },
};

export default config;
