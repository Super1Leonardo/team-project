<script lang="ts">
	import Heading from '$lib/components/ui/Heading.svelte';
	import ArticleList from '$lib/components/ArticleList.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import { minMlScore, timeframe } from '$lib/stores/filters';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let minMlScoreValue = $derived(parseFloat($minMlScore));

	let clusters = $derived(
		data.mentions
			.filter((m: any) => (m.ml_confidence ?? m.relevance_score ?? 0) >= minMlScoreValue)
			.map((m: any) => ({
				id: String(m.id),
				title: m.title,
				source: m.source_name || m.source || m.source_type || 'Unknown',
				publishedAt: m.published_at || m.publishedAt || '',
				sentiment: (m.sentiment || m.sentiment_label || 'neutral') as 'positive' | 'negative' | 'neutral',
				mlScore: Math.round((m.ml_confidence ?? m.relevance_score ?? 0) * 100),
				riskWords: m.risk_words || [],
				text: m.text || m.content || '',
				duplicates: []
			}))
	);
</script>

<div class="container mx-auto max-w-3xl py-4">
	<Heading>Лента упоминаний</Heading>

	<div class="mb-4">
		<FilterBar />
	</div>

	<ArticleList {clusters} />
</div>
