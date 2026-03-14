import { env } from "$env/dynamic/public";

import type {
	AppConfigResponse,
	AuthStatusResponse,
	ParseResponse,
	QrLoginResponse
} from "$lib/types/backend";

const DEFAULT_BACKEND_API_URL = "http://localhost:8000";

export function getBackendApiUrl() {
	return env.PUBLIC_BACKEND_API_URL || DEFAULT_BACKEND_API_URL;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`${getBackendApiUrl()}${path}`, {
		headers: {
			"Content-Type": "application/json",
			...(init?.headers ?? {})
		},
		...init
	});

	if (!response.ok) {
		let detail = "Backend request failed";
		try {
			const errorBody = (await response.json()) as { detail?: string };
			detail = errorBody.detail || detail;
		} catch {
			// Keep generic message when backend returns non-JSON.
		}
		throw new Error(detail);
	}

	return (await response.json()) as T;
}

export async function getBackendAppConfig() {
	return request<AppConfigResponse>("/api/app-config");
}

export async function getTelegramAuthStatus() {
	return request<AuthStatusResponse>("/api/telegram/auth/status");
}

export async function startQrLogin(recreate = false) {
	return request<QrLoginResponse>(`/api/telegram/auth/qr/start?recreate=${recreate}`, {
		method: "POST"
	});
}

export async function getQrLoginStatus() {
	return request<QrLoginResponse>("/api/telegram/auth/qr/status");
}

export async function submitQrPassword(password: string) {
	return request<QrLoginResponse>("/api/telegram/auth/qr/password", {
		method: "POST",
		body: JSON.stringify({ password })
	});
}

export async function cancelQrLogin() {
	return request<QrLoginResponse>("/api/telegram/auth/qr/cancel", {
		method: "POST"
	});
}

export async function logoutTelegram() {
	return request<{ authorized: boolean; message: string }>("/api/telegram/auth/logout", {
		method: "POST"
	});
}

export async function getParsedMessages(limitPerChannel = 10, channels?: string[]) {
	const params = new URLSearchParams({
		limit_per_channel: String(limitPerChannel)
	});

	for (const channel of channels ?? []) {
		params.append("channel", channel);
	}

	return request<ParseResponse>(`/api/messages?${params.toString()}`);
}
