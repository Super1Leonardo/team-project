import type { PageServerLoad } from './$types';

// Генератор моков, симулирующий агрегацию в ClickHouse (раздел 3 в ARCHITECTURE.md)
function generateMockTimeline(period: string) {
	const data = [];
	const now = new Date('2026-03-15T14:00:00Z'); // Фиксируем дату для предсказуемости
	
	let dataPoints = 7;
	let isHourly = false;

	if (period === '24h') {
		dataPoints = 24;
		isHourly = true;
	} else if (period === '30d') {
		dataPoints = 30;
	}

	for (let i = dataPoints - 1; i >= 0; i--) {
		const date = new Date(now);
		let dateStr = '';

		if (isHourly) {
			date.setHours(date.getHours() - i);
			// Формат: "2026-03-15 14:00"
			dateStr = date.toISOString().slice(0, 16).replace('T', ' '); 
		} else {
			date.setDate(date.getDate() - i);
			// Формат: "2026-03-15"
			dateStr = date.toISOString().split('T')[0];
		}

		// Симулируем инцидент (Spike) 10 марта или в один из часов для 24h
		const isSpike = dateStr === '2026-03-10' || (isHourly && i === 5);

		data.push({
			date: dateStr,
			positive: isSpike ? 5 : Math.floor(Math.random() * 15) + 5,
			neutral: isSpike ? 20 : Math.floor(Math.random() * 40) + 20,
			// Жесткий всплеск негатива
			negative: isSpike ? 85 : Math.floor(Math.random() * 10) + 1,
			// В день спайка модель обычно очень уверена из-за обилия риск-слов
			mlConfidence: isSpike ? 0.92 : 0.75 + Math.random() * 0.15
		});
	}

	return data;
}

export const load: PageServerLoad = async ({ url }) => {
	// 1. Читаем параметр из URL (куда SvelteKit сделал goto)
	const period = url.searchParams.get('period') || '7d';
	
	// 2. "Делаем запрос к ClickHouse" (генерируем данные под период)
	const timelineData = generateMockTimeline(period);
	
	// 3. Считаем KPI строго по тем данным, которые отдаем на клиент
	const totalMentions = timelineData.reduce((acc, curr) => acc + curr.positive + curr.negative + curr.neutral, 0);
	const avgScore = timelineData.reduce((acc, curr) => acc + curr.mlConfidence, 0) / timelineData.length;
	
	// Считаем спайки (дни/часы, где негатива > 50)
	const spikeAlertsCount = timelineData.filter(d => d.negative > 50).length;

	return {
		timeline: timelineData,
		kpi: {
			total: totalMentions,
			avgMlScore: (avgScore * 100).toFixed(1),
			spikeAlerts: spikeAlertsCount
		}
	};
};