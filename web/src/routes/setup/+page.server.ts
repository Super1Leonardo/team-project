import type { Actions, PageServerLoad } from './$types';

export interface Project {
	id: number;
	name: string;
	keywords: string[];
	exclude_keywords: string[];
	risk_words: string[];
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

let project = { ...mockProject };

export const load: PageServerLoad = async () => {
	return {
		project
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
	}
};
