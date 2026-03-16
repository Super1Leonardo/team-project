import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

export const translations = {
	sentiment: {
		positive: "позитивная",
		neutral: "нейтральная",
		negative: "негативная"
	},
	relevance: {
		relevant: "релевантно",
		irrelevant: "нерелелевантно"
	},
	alertType: {
		negative_spike: "всплеск негатива",
		volume_spike: "всплеск объёма",
		risk_word_spike: "всплеск риск-слов"
	},
	severity: {
		low: "низкий",
		medium: "средний",
		high: "высокий"
	},
	sourceType: {
		telegram: "Telegram",
		vk: "ВКонтакте",
		dzen: "Дзен",
		rss: "RSS",
		website: "Сайт"
	},
	sourceStatus: {
		ok: "Работает",
		error: "Ошибка",
		stale: "Неактивен"
	},
	eventType: {
		collector_started: "сбор запущен",
		collector_error: "ошибка сбора",
		ml_processed: "ML обработан",
		spike_detected: "всплеск обнаружен",
		alert_sent: "алерт отправлен",
		source_added: "источник добавлен",
		source_removed: "источник удалён"
	},
	sourceError: {
		"Feed timeout": "Таймаут чтения ленты",
		"VK API rate limit exceeded": "Превышен лимит VK API",
		"HTTP error 429": "Превышен лимит запросов",
		"HTTP error 401": "Ошибка авторизации",
		"HTTP error 403": "Доступ запрещён",
		"HTTP error 404": "Ресурс не найден",
		"Connection error": "Ошибка соединения",
		"Parse error": "Ошибка парсинга"
	},
	healthStatus: {
		healthy: "Работает",
		degraded: "Деградировал",
		unhealthy: "Не работает"
	},
	dbStatus: {
		healthy: "Работает",
		unhealthy: "Не работает"
	}
} as const;

export type SentimentLabel = keyof typeof translations.sentiment;
export type RelevanceLabel = keyof typeof translations.relevance;
export type AlertType = keyof typeof translations.alertType;
export type Severity = keyof typeof translations.severity;
export type SourceType = keyof typeof translations.sourceType;
export type SourceStatus = keyof typeof translations.sourceStatus;
export type EventType = keyof typeof translations.eventType;
export type SourceError = keyof typeof translations.sourceError;
export type HealthStatus = keyof typeof translations.healthStatus;
export type DbStatus = keyof typeof translations.dbStatus;

export function tSentiment(value: SentimentLabel): string {
	return translations.sentiment[value] ?? value;
}

export function tRelevance(value: RelevanceLabel): string {
	return translations.relevance[value] ?? value;
}

export function tAlertType(value: AlertType): string {
	return translations.alertType[value] ?? value;
}

export function tSeverity(value: Severity): string {
	return translations.severity[value] ?? value;
}

export function tSourceType(value: SourceType): string {
	return translations.sourceType[value] ?? value;
}

export function tSourceStatus(value: SourceStatus): string {
	return translations.sourceStatus[value] ?? value;
}

export function tEventType(value: EventType): string {
	return translations.eventType[value] ?? value;
}

export function tSourceError(value: string): string {
	return translations.sourceError[value as SourceError] ?? value;
}

export function tHealthStatus(value: string): string {
	return translations.healthStatus[value as HealthStatus] ?? value;
}

export function tDbStatus(value: string): string {
	return translations.dbStatus[value as DbStatus] ?? value;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChild<T> = T extends { child?: any } ? Omit<T, "child"> : T;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChildren<T> = T extends { children?: any } ? Omit<T, "children"> : T;
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>;
export type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & { ref?: U | null };
