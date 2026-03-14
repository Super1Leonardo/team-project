export type SourceType = "telegram" | "vk" | "dzen" | "rss";
export type RelevanceLabel = "relevant" | "irrelevant";
export type SentimentLabel = "positive" | "neutral" | "negative";

export interface Project {
	id: number;
	name: string;
	keywords: string[];
	exclude_keywords: string[];
	risk_words: string[];
	created_at: string;
	sources_count?: number | null;
	mentions_count?: number | null;
}

export interface CreateProjectPayload {
	name: string;
	keywords: string[];
	exclude_keywords?: string[];
	risk_words?: string[];
}

export interface UpdateProjectPayload {
	name?: string;
	keywords?: string[];
	exclude_keywords?: string[];
	risk_words?: string[];
}

export interface Source {
	id: number;
	project_id: number;
	source_type: SourceType;
	source_config: Record<string, unknown>;
	is_active: boolean;
	poll_interval_s: number;
	last_collected_at?: string | null;
	last_error?: string | null;
	created_at: string;
	raw_posts_count?: number | null;
}

export interface CreateSourcePayload {
	source_type: SourceType;
	source_config: Record<string, unknown>;
	is_active?: boolean;
	poll_interval_s?: number;
}

export interface UpdateSourcePayload {
	source_type?: SourceType;
	source_config?: Record<string, unknown>;
	is_active?: boolean;
	poll_interval_s?: number;
}

export interface CollectorRunRequest {
	source_ids?: number[];
	limit_per_source?: number;
}

export interface CollectorRunResponse {
	sources_checked: number;
	sources_processed: number;
	posts_saved: number;
	errors: Array<Record<string, unknown>>;
}

export interface CollectorTriggerResponse {
	status: "started";
	sources_triggered: number;
}

export interface CollectorSourceStatus extends Source {
	raw_posts_count: number;
	status: "ok" | "error" | "stale" | "idle";
}

export interface CollectorStatusResponse {
	ml_queue_size: number;
	sources: CollectorSourceStatus[];
}

export interface RawPost {
	id: number;
	source_id: number;
	source_type: SourceType;
	external_id: string;
	url?: string | null;
	title?: string | null;
	text: string;
	author?: string | null;
	published_at: string;
	collected_at: string;
	raw_meta: Record<string, unknown>;
	ml_processed: boolean;
}

export interface Mention {
	id: number;
	raw_post_id: number;
	project_id: number;
	source_id: number;
	source_type: SourceType;
	external_id: string;
	url?: string | null;
	title?: string | null;
	text: string;
	author?: string | null;
	published_at: string;
	collected_at: string;
	relevance_score: number;
	relevance_label: RelevanceLabel;
	sentiment_score: number;
	sentiment_label: SentimentLabel;
	has_risk_words: boolean;
	dedup_group_id?: number | null;
	is_primary: boolean;
	processed_at: string;
}

export interface MLQueueItem {
	raw_post_id: number;
	source_id: number;
	project_id: number;
	source_type: SourceType;
	external_id: string;
	url?: string | null;
	title?: string | null;
	text: string;
	author?: string | null;
	published_at: string;
	collected_at: string;
	raw_meta: Record<string, unknown>;
	keywords: string[];
	exclude_keywords: string[];
	risk_words: string[];
}

export interface MLQueueResponse {
	count: number;
	items: MLQueueItem[];
}

export interface MLResultWriteItem {
	raw_post_id: number;
	relevance_score: number;
	relevance_label: RelevanceLabel;
	sentiment_score: number;
	sentiment_label: SentimentLabel;
	has_risk_words?: boolean;
	embedding: number[];
	dedup_group_id?: number | null;
	is_primary?: boolean;
	processed_at?: string | null;
}

export interface MLResultsPushRequest {
	results: MLResultWriteItem[];
}

export interface MLResultsPushResponse {
	stored_count: number;
	synced_count: number;
	projects: Record<string, Record<string, number>>;
	message: string;
}

export interface MLLocalRunResponse {
	batch_size: number;
	stored_count: number;
	synced_count: number;
	projects: Record<string, Record<string, number>>;
}

export interface MLRemotePredictResponse {
	queued_count: number;
	remote_url: string;
	remote_results_count: number;
	stored_count?: number | null;
	synced_count?: number | null;
	projects: Record<string, Record<string, number>>;
	persisted: boolean;
	remote_response: unknown;
}

export interface BrandRadarHealthResponse {
	status: "healthy" | "degraded" | "unhealthy";
	postgres: "healthy" | "unhealthy";
	clickhouse: "healthy" | "unhealthy";
	ml_queue_size: number;
}
