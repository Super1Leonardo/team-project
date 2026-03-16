<script lang="ts">
	import { resolve } from '$app/paths';
	import Article from '$lib/components/Article.svelte';

	// Типы данных (взяты из твоего +page.svelte)
	export interface Duplicate {
		source: string;
		publishedAt: string;
		title: string;
		mlScore: number;
	}

	export interface Cluster {
		id: string;
		title: string;
		source: string;
		publishedAt: string;
		sentiment: 'positive' | 'negative' | 'neutral';
		mlScore: number;
		riskWords: string[];
		text: string;
		duplicates: Duplicate[];
	}

	// Svelte 5 Rune для приема массива с дефолтным пустым значением
	let { clusters = [] }: { clusters: Cluster[] } = $props();
</script>

<div class="flex flex-col gap-4">
	{#if clusters.length === 0}
		<div
			class="flex h-32 items-center justify-center rounded-lg border border-dashed border-border text-sm text-muted-foreground mt-4"
		>
			Нет упоминаний по заданным фильтрам
		</div>
	{:else}
		{#each clusters as clusterData (clusterData.id)}
			<Article cluster={clusterData} />
		{/each}
	{/if}
</div>
