import type {
	BrandRadarHealthResponse,
	CollectorRunRequest,
	CollectorStatusResponse,
	CollectorTriggerResponse,
	CreateProjectPayload,
	CreateSourcePayload,
	MLRunResponse,
	MLQueueResponse,
	MLRemotePredictResponse,
	MLResultsPushRequest,
	MLResultsPushResponse,
	Mention,
	Project,
	RawPost,
	Source,
	UpdateProjectPayload,
	UpdateSourcePayload
} from "$lib/types/brandradar";

export class BrandRadarApiError extends Error {
	status: number;
	payload: unknown;

	constructor(message: string, status: number, payload: unknown) {
		super(message);
		this.name = "BrandRadarApiError";
		this.status = status;
		this.payload = payload;
	}
}

export interface BrandRadarClientOptions {
	baseUrl?: string;
	fetchImpl?: typeof fetch;
	headers?: HeadersInit;
}

interface ApiEnvelope<T> {
	data: T;
	meta?: {
		total?: number | null;
		page?: number | null;
		page_size?: number | null;
	} | null;
}

interface ApiErrorEnvelope {
	error?: {
		code?: string;
		message?: string;
	};
	detail?: string;
}

function normalizeBaseUrl(baseUrl?: string): string {
	const raw = baseUrl ?? import.meta.env.PUBLIC_BRANDRADAR_API_BASE_URL ?? "http://localhost:8000";
	return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

function buildUrl(baseUrl: string, path: string, query?: Record<string, string | number | boolean | null | undefined>) {
	const url = new URL(`${baseUrl}${path}`);
	if (query) {
		for (const [key, value] of Object.entries(query)) {
			if (value !== undefined && value !== null) {
				url.searchParams.set(key, String(value));
			}
		}
	}
	return url.toString();
}

export function createBrandRadarClient(options: BrandRadarClientOptions = {}) {
	const baseUrl = normalizeBaseUrl(options.baseUrl);
	const fetchImpl = options.fetchImpl ?? fetch;
	const defaultHeaders = options.headers ?? {};

	async function request<T>(path: string, init?: RequestInit, query?: Record<string, string | number | boolean | null | undefined>): Promise<T> {
		const response = await fetchImpl(buildUrl(baseUrl, path, query), {
			...init,
			headers: {
				"content-type": "application/json",
				...defaultHeaders,
				...(init?.headers ?? {})
			}
		});

		if (!response.ok) {
			let payload: unknown = null;
			try {
				payload = await response.json();
			} catch {
				payload = await response.text();
			}
			const apiPayload = payload as ApiErrorEnvelope | null;
			const message =
				apiPayload?.error?.message ??
				apiPayload?.detail ??
				response.statusText;
			throw new BrandRadarApiError(message, response.status, payload);
		}

		if (response.status === 204) {
			return undefined as T;
		}

		const payload = (await response.json()) as T | ApiEnvelope<T>;
		if (typeof payload === "object" && payload !== null && "data" in payload) {
			return (payload as ApiEnvelope<T>).data;
		}
		return payload as T;
	}

	return {
		listProjects: () => request<Project[]>("/api/projects"),
		getProject: (projectId: number) =>
			request<Project>(`/api/projects/${projectId}`),
		createProject: (payload: CreateProjectPayload) =>
			request<Project>("/api/projects", {
				method: "POST",
				body: JSON.stringify(payload)
			}),
		updateProject: (projectId: number, payload: UpdateProjectPayload) =>
			request<Project>(`/api/projects/${projectId}`, {
				method: "PUT",
				body: JSON.stringify(payload)
			}),
		deleteProject: (projectId: number) =>
			request<void>(`/api/projects/${projectId}`, {
				method: "DELETE"
			}),
		listSources: (projectId: number) =>
			request<Source[]>(`/api/projects/${projectId}/sources`),
		getSource: (projectId: number, sourceId: number) =>
			request<Source>(`/api/projects/${projectId}/sources/${sourceId}`),
		createSource: (projectId: number, payload: CreateSourcePayload) =>
			request<Source>(`/api/projects/${projectId}/sources`, {
				method: "POST",
				body: JSON.stringify(payload)
			}),
		updateSource: (projectId: number, sourceId: number, payload: UpdateSourcePayload) =>
			request<Source>(`/api/projects/${projectId}/sources/${sourceId}`, {
				method: "PUT",
				body: JSON.stringify(payload)
			}),
		deleteSource: (projectId: number, sourceId: number) =>
			request<void>(`/api/projects/${projectId}/sources/${sourceId}`, {
				method: "DELETE"
			}),
		runCollectorOnce: (projectId: number, payload: CollectorRunRequest) =>
			request<CollectorTriggerResponse>(`/api/projects/${projectId}/collect`, {
				method: "POST",
				body: JSON.stringify(payload)
			}),
		getCollectorStatus: (projectId: number) =>
			request<CollectorStatusResponse>(
				`/api/projects/${projectId}/collector/status`
			),
		getMlQueue: (limit = 100) =>
			request<MLQueueResponse>("/api/ml/queue", undefined, { limit }),
		pushMlResults: (payload: MLResultsPushRequest) =>
			request<MLResultsPushResponse>("/api/ml/results", {
				method: "POST",
				body: JSON.stringify(payload)
			}),
		runMl: (limit = 100) =>
			request<MLRunResponse>("/api/ml/run", {
				method: "POST"
			}, { limit }),
		runLocalMl: (limit = 100) =>
			request<MLRunResponse>("/api/ml/run", {
				method: "POST"
			}, { limit }),
		predictRemoteMl: (limit = 100, persist = true) =>
			request<MLRemotePredictResponse>("/api/ml/predict", {
				method: "POST"
			}, { limit, persist }),
		listRawPosts: (projectId: number, limit = 100) =>
			request<RawPost[]>(`/api/projects/${projectId}/raw-posts`, undefined, { limit }),
		listMentions: (projectId: number, limit = 100) =>
			request<Mention[]>(`/api/projects/${projectId}/mentions`, undefined, { limit }),
		getHealth: () => request<BrandRadarHealthResponse>("/api/health")
	};
}
