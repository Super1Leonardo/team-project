# syntax=docker/dockerfile:1.7

# 1. Install all dependencies
FROM oven/bun:1 AS deps
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile --ignore-scripts

# 2. Build the application
FROM deps AS build
# --- RELEVANT CHANGE START ---
# Define ARGs here so they can be passed from docker-compose
ARG PUBLIC_BRANDRADAR_API_BASE_URL
# Set them as ENV so the 'bun run build' process can see them
ENV PUBLIC_BRANDRADAR_API_BASE_URL=$PUBLIC_BRANDRADAR_API_BASE_URL
# --- RELEVANT CHANGE END ---

COPY . .
RUN bun run prepare
RUN bun run build

# 3. Install production-only dependencies
FROM oven/bun:1 AS prod-deps
WORKDIR /app
COPY package.json bun.lock ./
RUN mkdir -p node_modules && bun install --frozen-lockfile --production --ignore-scripts

# 4. Playwright stage for E2E testing (optional/separate)
FROM mcr.microsoft.com/playwright:v1.58.2-noble AS playwright
WORKDIR /app
COPY --from=deps /usr/local/bin/bun /usr/local/bin/bun
COPY package.json bun.lock ./
RUN bun install --ignore-scripts
COPY . .
CMD ["bun", "run", "test:e2e"]

# 5. Final Runner stage
FROM oven/bun:1 AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOST=0.0.0.0
ENV PORT=3000

# Copy only what is needed to run the app
COPY --from=prod-deps /app/node_modules ./node_modules
COPY --from=build /app/build ./build
COPY --from=build /app/package.json ./package.json

EXPOSE 3000
CMD ["bun", "build/index.js"]
