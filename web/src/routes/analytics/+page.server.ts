import type { PageServerLoad } from './$types';
import { mockAnalyticsTimeline } from '$lib/server/mockData';

export const load: PageServerLoad = async () => {
	// В реальном проде здесь будет запрос к API: GET /api/analytics?timeframe=7d
	// И расчет общих метрик (total, avg score) на стороне БД/Бэкенда
	
	const totalMentions = mockAnalyticsTimeline.reduce((acc, curr) => acc + curr.positive + curr.negative + curr.neutral, 0);
	const avgScore = mockAnalyticsTimeline.reduce((acc, curr) => acc + curr.mlConfidence, 0) / mockAnalyticsTimeline.length;

	return {
		timeline: mockAnalyticsTimeline,
		kpi: {
			total: totalMentions,
			avgMlScore: (avgScore * 100).toFixed(1),
			spikeAlerts: 1 // Захардкодим 1 для презентации инцидента 10 марта
		}
	};
};