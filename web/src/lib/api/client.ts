export interface ApiClientConfig {
	timeout: number;
	retries: number;
	retryDelay: number;
}

export interface ApiError {
	message: string;
	status?: number;
	code?: string;
}

export interface ApiResponse<T> {
	data?: T;
	error?: ApiError;
}

const DEFAULT_CONFIG: ApiClientConfig = {
	timeout: 10000,
	retries: 3,
	retryDelay: 1000,
};

function parseJsonPayload(text: string): unknown {
	const withoutBom = text.replace(/^\uFEFF/, '');
	const trimmed = withoutBom.trim();
	if (!trimmed) {
		return null;
	}

	try {
		return JSON.parse(trimmed);
	} catch (error) {
		const firstJsonCharIndex = trimmed.search(/[\[{]/);
		if (firstJsonCharIndex > 0) {
			return JSON.parse(trimmed.slice(firstJsonCharIndex));
		}
		throw error;
	}
}

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function fetchApi<T>(
	url: string,
	options?: RequestInit,
	config?: Partial<ApiClientConfig>
): Promise<ApiResponse<T>> {
	const cfg = { ...DEFAULT_CONFIG, ...config };
	let lastError: ApiError | undefined;

	for (let attempt = 0; attempt <= cfg.retries; attempt++) {
		const controller = new AbortController();
		const timeoutId = setTimeout(() => controller.abort(), cfg.timeout);

		try {
			const response = await fetch(url, {
				...options,
				signal: controller.signal,
			});

			clearTimeout(timeoutId);
			const responseText = await response.text();

			if (!response.ok) {
				const status = response.status;
				let message = `Ошибка ${status}`;

				try {
					const errorData = parseJsonPayload(responseText) as
						| { detail?: string; message?: string }
						| null;
					message = errorData?.detail || errorData?.message || message;
				} catch {
					// Response wasn't JSON
				}

				lastError = { message, status, code: 'HTTP_ERROR' };

				// Don't retry client errors (4xx)
				if (status >= 400 && status < 500) {
					return { error: lastError };
				}

				// Retry server errors (5xx) and network errors
				if (attempt < cfg.retries) {
					await sleep(cfg.retryDelay * (attempt + 1)); // Exponential backoff
					continue;
				}

				return { error: lastError };
			}

			const data = parseJsonPayload(responseText) as
				| { data?: T }
				| T
				| null;
			return { data: (data && typeof data === 'object' && 'data' in data ? data.data : data) as T };
		} catch (error) {
			clearTimeout(timeoutId);

			if (error instanceof Error) {
				if (error.name === 'AbortError') {
					lastError = { message: 'Превышен таймаут запроса', code: 'TIMEOUT' };
				} else if (error.name === 'TypeError' && error.message.includes('fetch')) {
					lastError = { message: 'Нет подключения к интернету', code: 'NETWORK_ERROR' };
				} else {
					lastError = { message: error.message, code: 'UNKNOWN' };
				}
			} else {
				lastError = { message: 'Неизвестная ошибка', code: 'UNKNOWN' };
			}

			if (attempt < cfg.retries) {
				await sleep(cfg.retryDelay * (attempt + 1));
				continue;
			}

			return { error: lastError };
		}
	}

	return { error: lastError };
}

export const api = {
	get: <T>(url: string, config?: Partial<ApiClientConfig>) =>
		fetchApi<T>(url, { method: 'GET' }, config),

	post: <T>(url: string, body: unknown, config?: Partial<ApiClientConfig>) =>
		fetchApi<T>(url, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body),
		}, config),

	patch: <T>(url: string, body: unknown, config?: Partial<ApiClientConfig>) =>
		fetchApi<T>(url, {
			method: 'PATCH',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body),
		}, config),

	delete: <T>(url: string, config?: Partial<ApiClientConfig>) =>
		fetchApi<T>(url, { method: 'DELETE' }, config),
};
