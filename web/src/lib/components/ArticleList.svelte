<script lang="ts" module>
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
		hasRiskWords: boolean;
		text: string;
		duplicates: Duplicate[];
	}
</script>

<script lang="ts">
	import Article from '$lib/components/Article.svelte';

	let { clusters = [] }: { clusters: Cluster[] } = $props();
</script>

<div class="flex flex-col gap-4">
	{#if clusters.length === 0}
		<div class="rounded-lg border bg-card py-8 text-center text-muted-foreground">
			Нет данных для отображения по выбранным фильтрам
		</div>
	{:else}
		{#each clusters as clusterData (clusterData.id)}
			<Article cluster={clusterData} />
		{/each}
	{/if}
</div>
