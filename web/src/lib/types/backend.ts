export type UserInfo = {
	id: number;
	username: string | null;
	phone: string | null;
	first_name: string | null;
	last_name: string | null;
};

export type AuthStatusResponse = {
	configured: boolean;
	authorized: boolean;
	phone_hint: string | null;
	user: UserInfo | null;
	selected_channels: string[];
};

export type AppConfigResponse = {
	api_title: string;
	api_version: string;
	public_api_url: string;
	selected_channels: string[];
	auth_methods: {
		code: boolean;
		qr: boolean;
	};
	docs_url: string;
	health_url: string;
};

export type QrLoginResponse = {
	authorized: boolean;
	status: string;
	message: string;
	user: UserInfo | null;
	qr_url: string | null;
	qr_image_data_url: string | null;
	expires_at: string | null;
	error: string | null;
	next_step: string | null;
};

export type ReactionInfo = {
	key: string;
	count: number;
	type: string;
};

export type MessageSource = {
	channel_id: number;
	title: string;
	username: string | null;
	requested_as: string;
};

export type ParsedMessage = {
	id: number;
	text: string;
	date: string;
	views: number | null;
	forwards: number | null;
	post_author: string | null;
	url: string | null;
	like_count: number | null;
	dislike_count: number | null;
	reactions: ReactionInfo[];
	source: MessageSource;
};

export type ChannelParseResult = {
	requested_as: string;
	title: string | null;
	username: string | null;
	status: string;
	error: string | null;
	messages: ParsedMessage[];
};

export type ParseResponse = {
	authorized: boolean;
	count: number;
	channels: string[];
	items: ParsedMessage[];
	results: ChannelParseResult[];
};
