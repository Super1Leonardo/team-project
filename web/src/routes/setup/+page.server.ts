import type { Actions, PageServerLoad } from './$types';

export interface Project {
	id: number;
	name: string;
	keywords: string[];
	exclude_keywords: string[];
	risk_words: string[];
	created_at: string;
}

export interface Source {
	id: number;
	project_id: number;
	source_type: 'telegram' | 'vk' | 'dzen' | 'rss';
	source_config: {
		channel?: string;
		group_id?: number;
		domain?: string;
		feed_url?: string;
	};
	is_active: boolean;
	poll_interval_s: number;
	last_collected_at: string | null;
	last_error: string | null;
	created_at: string;
}

const mockProject: Project = {
	id: 1,
	name: 'Brand Radar',
	keywords: ['сбербанк', 'sberbank', 'сбер'],
	exclude_keywords: ['сберкнижка', 'сбермаркет'],
	risk_words: ['утечка', 'мошенники', 'сбой', 'взлом', 'штраф'],
	created_at: '2026-01-15T10:00:00Z'
};

const mockSources: Source[] = [
	{
		id: 1,
		project_id: 1,
		source_type: 'telegram',
		source_config: { channel: 'banksta' },
		is_active: true,
		poll_interval_s: 300,
		last_collected_at: '2026-03-14T15:30:00Z',
		last_error: null,
		created_at: '2026-01-15T10:05:00Z'
	},
	{
		id: 2,
		project_id: 1,
		source_type: 'vk',
		source_config: { group_id: -12345, domain: 'bank_news' },
		is_active: true,
		poll_interval_s: 300,
		last_collected_at: '2026-03-14T15:28:00Z',
		last_error: null,
		created_at: '2026-01-16T11:00:00Z'
	},
	{
		id: 3,
		project_id: 1,
		source_type: 'rss',
		source_config: { feed_url: 'https://example.com/rss' },
		is_active: false,
		poll_interval_s: 600,
		last_collected_at: '2026-03-14T10:00:00Z',
		last_error: 'Feed timeout',
		created_at: '2026-01-17T09:00:00Z'
	}
];

let project = { ...mockProject };
let sources = [...mockSources];
let nextSourceId = 4;

export const load: PageServerLoad = async () => {
	return {
		project,
		sources
	};
};

export const actions: Actions = {
	updateProject: async ({ request }) => {
		const data = await request.formData();
		
		const keywordsStr = data.get('keywords') as string;
		const excludeKeywordsStr = data.get('exclude_keywords') as string;
		const riskWordsStr = data.get('risk_words') as string;

		project = {
			...project,
			keywords: keywordsStr.split(',').map(k => k.trim()).filter(k => k),
			exclude_keywords: excludeKeywordsStr.split(',').map(k => k.trim()).filter(k => k),
			risk_words: riskWordsStr.split(',').map(k => k.trim()).filter(k => k)
		};

		return { success: true, message: 'Настройки сохранены', project };
	},

	addSource: async ({ request }) => {
		const data = await request.formData();
		
		const sourceType = data.get('source_type') as Source['source_type'];
		const channel = data.get('channel') as string;
		const groupId = data.get('group_id') as string;
		const domain = data.get('domain') as string;
		const feedUrl = data.get('feed_url') as string;
		const pollInterval = parseInt(data.get('poll_interval') as string) || 300;

		const sourceConfig: Source['source_config'] = {};
		
		if (sourceType === 'telegram' && channel) {
			sourceConfig.channel = channel;
		} else if (sourceType === 'vk' && groupId) {
			sourceConfig.group_id = parseInt(groupId);
			if (domain) sourceConfig.domain = domain;
		} else if (sourceType === 'rss' && feedUrl) {
			sourceConfig.feed_url = feedUrl;
		}

		const newSource: Source = {
			id: nextSourceId++,
			project_id: 1,
			source_type: sourceType,
			source_config: sourceConfig,
			is_active: true,
			poll_interval_s: pollInterval,
			last_collected_at: null,
			last_error: null,
			created_at: new Date().toISOString()
		};

		sources = [...sources, newSource];

		return { success: true, message: 'Источник добавлен' };
	},

	toggleSource: async ({ request }) => {
		const data = await request.formData();
		const sourceId = parseInt(data.get('source_id') as string);

		sources = sources.map(s => 
			s.id === sourceId ? { ...s, is_active: !s.is_active } : s
		);

		return { success: true };
	},

	deleteSource: async ({ request }) => {
		const data = await request.formData();
		const sourceId = parseInt(data.get('source_id') as string);

		sources = sources.filter(s => s.id !== sourceId);

		return { success: true, message: 'Источник удалён' };
	}
};
