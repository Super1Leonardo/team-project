<script lang="ts">
	import Article from '$lib/components/Article.svelte';
	import type { MentionCluster } from '$lib/types/brandradar';

	const now = '2026-03-17T09:36:50.000Z';

	const cluster: MentionCluster = {
		cluster_id: 6,
		dedup_group_id: 6,
		mentions_count: 3,
		first_seen_at: now,
		last_seen_at: now,
		representative_mention_id: 100,
		id: 100,
		raw_post_id: 501,
		project_id: 2,
		source_id: 10,
		source_type: 'website',
		external_id: 'cluster-demo-1',
		url: 'https://example.com/demo-cluster',
		title: 'Тестовый кластер',
		text: 'Демо-карточка для e2e-проверки загрузки дублей.',
		author: 'Demo',
		published_at: now,
		collected_at: now,
		relevance_score: 0.92,
		relevance_label: 'relevant',
		sentiment_score: 0.61,
		sentiment_label: 'negative',
		has_risk_words: false,
		processed_at: now
	};
</script>

<div class="mx-auto max-w-3xl p-6">
	<h1 class="mb-4 text-2xl font-semibold">E2E Cluster Fixture</h1>
	<Article {cluster} />
</div>
