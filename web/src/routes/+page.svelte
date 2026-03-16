<script lang="ts">
	import Heading from '$lib/components/ui/Heading.svelte';
	import ArticleList from '$lib/components/ArticleList.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import type { PageData } from './$types';
	import type { Cluster } from '$lib/components/ArticleList.svelte';

	// Строгий контракт ответа от API (на базе схемы БД из diff.txt и ARCHITECTURE.md)
	interface BackendMention {
		id: number;
		raw_post_id: number;
		project_id: number;
		source_id: number;
		source_type: 'telegram' | 'vk' | 'dzen' | 'rss';
		source_name?: string; // может приходить из JOIN
		url: string | null;
		title: string | null;
		text: string;
		author: string | null;
		published_at: string;
		relevance_score: number;
		relevance_label: string;
		sentiment_score: number;
		sentiment_label: 'positive' | 'neutral' | 'negative';
		has_risk_words: boolean;
		risk_words?: string[];
		dedup_group_id: number | null;
		is_primary: boolean;
		dedup?: { duplicates: any[] }; // Если бэкенд отдает вложенные дубли
	}

	let { data }: { data: PageData } = $props();

	// Трансформируем строгий ответ бэкенда в формат пропсов компонента ArticleList
	let clusters: Cluster[] = $derived(
		(data.mentions as BackendMention[]).map((m) => ({
			id: String(m.id),
			title: m.title || '',
			source: m.source_name || m.source_type,
			publishedAt: m.published_at,
			sentiment: m.sentiment_label,
			mlScore: Math.round(m.relevance_score * 100),
			hasRiskWords: m.has_risk_words,
			text: m.text,
			duplicates: m.dedup?.duplicates || []
		}))
	);
</script>

<div class="container mx-auto max-w-3xl py-4">
	<div class="mb-6 flex w-full flex-col items-center">
		<Heading>Лента</Heading>

		<FilterBar />
	</div>

	<ArticleList {clusters} />
</div>
