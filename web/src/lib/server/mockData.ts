// src/lib/server/mockData.ts
import type { Cluster } from '$lib/components/ArticleList.svelte';

// 1. Данные для главной страницы (Лента) - теперь за 7 дней с разным ML Score
export const mockClusters: Cluster[] = [
	// --- 14 Марта ---
	{
		id: 'cl-10492',
		title: 'Массовый сбой в платежном шлюзе',
		source: 'Telegram: Финтех Инсайды',
		publishedAt: '2026-03-14T09:45:00Z',
		sentiment: 'negative',
		mlScore: 0.95,
		riskWords: ['сбой', 'лежат сервера', 'ошибка 500'],
		text: 'Клиенты массово жалуются на невозможность провести оплату через терминалы...',
		duplicates: [
			{ title: 'Терминалы не принимают карты', source: 'VK: Подслушано Бизнес', publishedAt: '2026-03-14T09:50:00Z', mlScore: 0.82 }
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
		text: 'Банк анонсировал беспрецедентные условия по дебетовым картам...',
		duplicates: []
	},
	// --- 13 Марта ---
	{
		id: 'cl-10480',
		title: 'Итоги квартала: прибыль выросла на 12%',
		source: 'Ведомости',
		publishedAt: '2026-03-13T14:00:00Z',
		sentiment: 'positive',
		mlScore: 0.92,
		riskWords: [],
		text: 'Финансовые показатели превзошли ожидания аналитиков...',
		duplicates: []
	},
	{
		id: 'cl-10481',
		title: 'Слухи о сокращениях в IT-отделе',
		source: 'Дзен: IT-кухня',
		publishedAt: '2026-03-13T16:30:00Z',
		sentiment: 'neutral',
		mlScore: 0.55, // Специально низкий скор для проверки фильтра
		riskWords: ['сокращения', 'увольнения'],
		text: 'На форумах обсуждают возможную оптимизацию штата разработчиков...',
		duplicates: []
	},
	// --- 12 Марта ---
	{
		id: 'cl-10475',
		title: 'Интеграция с Госуслугами работает с перебоями',
		source: 'Telegram: Госуслуги Info',
		publishedAt: '2026-03-12T11:15:00Z',
		sentiment: 'negative',
		mlScore: 0.78,
		riskWords: ['перебои', 'не работает'],
		text: 'Пользователи не могут авторизоваться через ЕСИА уже несколько часов.',
		duplicates: []
	},
	// --- 10 Марта (SPIKE ИНЦИДЕНТ) ---
	{
		id: 'cl-10460',
		title: 'Крупнейшая утечка базы клиентов!',
		source: 'Telegram: Утечки Инфо',
		publishedAt: '2026-03-10T08:00:00Z',
		sentiment: 'negative',
		mlScore: 0.99,
		riskWords: ['утечка', 'база данных', 'хакеры'],
		text: 'В сеть слили базу на 5 миллионов строк с персональными данными клиентов банка.',
		duplicates: [
			{ title: 'Данные клиентов продают в даркнете', source: 'VK: Типичный Хакер', publishedAt: '2026-03-10T08:15:00Z', mlScore: 0.95 },
			{ title: 'Банк отрицает взлом', source: 'Коммерсантъ', publishedAt: '2026-03-10T10:00:00Z', mlScore: 0.85 }
		]
	},
	{
		id: 'cl-10461',
		title: 'ЦБ начал проверку после сообщений об утечке',
		source: 'Интерфакс',
		publishedAt: '2026-03-10T12:00:00Z',
		sentiment: 'negative',
		mlScore: 0.94,
		riskWords: ['проверка ЦБ', 'штраф', 'утечка'],
		text: 'Регулятор запросил информацию у банка в связи с инцидентом ИБ...',
		duplicates: []
	},
	// --- 8 Марта ---
	{
		id: 'cl-10450',
		title: 'Поздравление с 8 марта от CEO',
		source: 'VK: Официальная группа',
		publishedAt: '2026-03-08T09:00:00Z',
		sentiment: 'positive',
		mlScore: 0.99,
		riskWords: [],
		text: 'Дорогие женщины, поздравляем вас с Международным женским днем!',
		duplicates: []
	}
];

// 2. Агрегированные данные для страницы Аналитики (Таймлайн)
// Расширено под разные значения mlConfidence для проверки реактивности графика
export const mockAnalyticsTimeline = [
	{ date: '2026-03-08', positive: 120, neutral: 45, negative: 15, mlConfidence: 0.92 },
	{ date: '2026-03-09', positive: 132, neutral: 50, negative: 18, mlConfidence: 0.89 },
	{ date: '2026-03-10', positive: 101, neutral: 40, negative: 189, mlConfidence: 0.95 }, // Spike!
	{ date: '2026-03-11', positive: 145, neutral: 55, negative: 40, mlConfidence: 0.65 }, // Низкая уверенность
	{ date: '2026-03-12', positive: 160, neutral: 60, negative: 22, mlConfidence: 0.75 }, 
	{ date: '2026-03-13', positive: 150, neutral: 58, negative: 18, mlConfidence: 0.55 }, // Низкая уверенность
	{ date: '2026-03-14', positive: 170, neutral: 45, negative: 12, mlConfidence: 0.96 }
];