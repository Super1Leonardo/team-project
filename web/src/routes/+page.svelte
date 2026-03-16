<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import Heading from '$lib/components/ui/Heading.svelte';
	import ArticleList from '$lib/components/ArticleList.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import { Button } from '$lib/components/ui/shadcn/button';
	import type { PageData } from './$types';
	import type { Cluster } from '$lib/components/ArticleList.svelte';

	interface BackendMention {
		id: number;
		raw_post_id: number;
		project_id: number;
		source_id: number;
		source_type: 'telegram' | 'vk' | 'dzen' | 'rss';
		source_name?: string;
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
		dedup?: { duplicates: any[] };
	}

	let { data }: { data: PageData } = $props();

	let clusters: Cluster[] = $derived(
		((data.mentions as BackendMention[]) || []).map((m) => ({
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

	const hasError = $derived(!!data.error);
</script>

<div class="container mx-auto max-w-3xl py-4" data-testid="feed-container">
	<div class="mb-6 flex w-full flex-col items-center">
		<div data-testid="page-heading">
			<Heading>Лента</Heading>
		</div>

		<FilterBar data-testid="feed-filters" />
	</div>

	{#if hasError}
		<div
			data-testid="error-container"
			class="rounded-lg border border-destructive bg-destructive/10 p-6 text-center"
		>
			<p data-testid="error-message" class="mb-4 text-destructive">
				{data.error?.message || 'Произошла ошибка при загрузке данных'}
			</p>
			<Button data-testid="retry-button" variant="outline" onclick={() => invalidateAll()}>
				Повторить
			</Button>
		</div>
	{:else}
		<div data-testid="article-list-wrapper">
			<ArticleList {clusters} />
		</div>
	{/if}
</div>
