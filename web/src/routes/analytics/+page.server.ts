import type { PageServerLoad } from './$types';
import { api } from '$lib/api/client';

const API_BASE_URL = process.env.PUBLIC_BRANDRADAR_API_BASE_URL || 'http://localhost:8000';

export const load: PageServerLoad = async ({ url }) => {
	let timeline: any[] = [];
	let kpi = { total: 0, avgMlScore: '0.0', spikeAlerts: 0 };
	let error: string | undefined;

	const urlConfidence = url.searchParams.get('confidence');
	const urlPeriod = url.searchParams.get('period');
	const sentiment = url.searchParams.get('sentiment');

	const confidence = urlConfidence || '0.7';
	const period = urlPeriod || '7d';

	const queryParams = new URLSearchParams({
		limit: '500',
		confidence,
		period,
		primary_only: 'false',
		relevant_only: 'false',
		include_total: 'false',
	});
	if (sentiment) queryParams.set('sentiment', sentiment);

	const mentionsRes = await api.get<any[]>(
		`${API_BASE_URL}/api/feed?${queryParams.toString()}`
	);

	if (mentionsRes.error) {
		error = mentionsRes.error.message;
	} else {
		const mentions = mentionsRes.data ?? [];
		kpi.total = mentions.length;

		let totalScore = 0;
		const daysMap: Record<string, any> = {};

		mentions.forEach((m) => {
			const score = m.relevance_score ?? m.ml_confidence ?? 0;
			totalScore += score;

			const dateStr = new Date(m.published_at || m.publishedAt).toISOString().split('T')[0];
			if (!daysMap[dateStr]) {
				daysMap[dateStr] = {
					date: dateStr,
					positive: 0,
					negative: 0,
					neutral: 0,
					mlConfidenceSum: 0,
					count: 0,
				};
			}

			const sentiment = m.sentiment_label ?? m.sentiment ?? 'neutral';
			if (sentiment === 'positive') daysMap[dateStr].positive++;
			else if (sentiment === 'negative') daysMap[dateStr].negative++;
			else daysMap[dateStr].neutral++;

			daysMap[dateStr].mlConfidenceSum += score;
			daysMap[dateStr].count++;
		});

		kpi.avgMlScore = mentions.length > 0 ? ((totalScore / mentions.length) * 100).toFixed(1) : '0.0';

		timeline = Object.values(daysMap)
			.map((d: any) => ({
				date: d.date,
				positive: d.positive,
				negative: d.negative,
				neutral: d.neutral,
				mlConfidence: d.count > 0 ? d.mlConfidenceSum / d.count : 0,
			}))
			.sort((a: any, b: any) => a.date.localeCompare(b.date));
	}

	return {
		timeline,
		kpi,
		error: error ? { message: error } : undefined,
	};
};
