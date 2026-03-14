import type { PageServerLoad } from './$types';
import type { Cluster } from '$lib/components/ArticleList.svelte';

const mockClusters: Cluster[] = [
	{
		id: 'cl-10492',
		title: 'Массовый сбой в платежном шлюзе',
		source: 'Telegram: Финтех Инсайды',
		publishedAt: '2026-03-14T09:45:00Z',
		sentiment: 'negative',
		mlScore: 0.65,
		riskWords: ['сбой', 'лежат сервера', 'ошибка 500', 'убытки'],
		text: 'Клиенты массово жалуются на невозможность провести оплату через терминалы. Поддержка не отвечает уже 40 минут. Предварительный ущерб оценивается в миллионы.',
		duplicates: [
			{
				title: 'Терминалы не принимают карты',
				source: 'VK: Подслушано Бизнес',
				publishedAt: '2026-03-14T09:50:00Z',
				mlScore: 0.82
			},
			{
				title: 'Ошибка 500 при попытке оплаты',
				source: 'Twitter / X',
				publishedAt: '2026-03-14T09:55:00Z',
				mlScore: 0.91
			}
		]
	},
	{
		id: 'cl-10493',
		title: 'Запуск новой программы лояльности «Кешбэк 10%»',
		source: 'РБК Инвестиции',
		publishedAt: '2026-03-14T10:20:00Z',
		sentiment: 'positive',
		mlScore: 0.98,
		riskWords: [],
		text: 'Банк анонсировал беспрецедентные условия по дебетовым картам. Пользователи соцсетей крайне позитивно встретили новость, отмечая выгодные условия по сравнению с конкурентами.',
		duplicates: [
			{
				title: 'Обзор нового кешбэка от Brand Bank',
				source: 'Habr',
				publishedAt: '2026-03-14T10:45:00Z',
				mlScore: 0.88
			}
		]
	},
	{
		id: 'cl-10494',
		title: 'Плановые технические работы 15 марта',
		source: 'Официальный сайт',
		publishedAt: '2026-03-14T11:00:00Z',
		sentiment: 'neutral',
		mlScore: 0.85,
		riskWords: ['техработы'],
		text: 'Завтра с 02:00 до 04:00 по московскому времени возможны краткосрочные прерывания в работе мобильного приложения в связи с обновлением инфраструктуры.',
		duplicates: []
	},
	{
		id: 'cl-10495',
		title: 'Слухи о покупке крупного ритейлера',
		source: 'Bloomberg Online',
		publishedAt: '2026-03-14T11:30:00Z',
		sentiment: 'neutral',
		mlScore: 0.42,
		riskWords: ['неподтвержденная информация', 'инсайды'],
		text: 'В сети появилась информация о возможных переговорах по поглощению сети магазинов "ВкусМаркет". Официальные представители компаний пока воздерживаются от комментариев.',
		duplicates: [
			{
				title: 'Акции ВкусМаркета растут на слухах о сделке',
				source: 'Telegram: Market Watch',
				publishedAt: '2026-03-14T11:40:00Z',
				mlScore: 0.75
			}
		]
	}
];

export const load: PageServerLoad = async () => {
	return {
		clusters: mockClusters
	};
};