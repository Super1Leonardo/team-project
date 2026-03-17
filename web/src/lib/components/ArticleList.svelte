<script lang="ts" module>
	import type { MentionCluster } from '$lib/types/brandradar';

	export type Cluster = MentionCluster;
</script>

<script lang="ts">
	import Article from '$lib/components/Article.svelte';

	let { clusters = [] }: { clusters: Cluster[] } = $props();
</script>

<div class="flex flex-col gap-4">
	{#if clusters.length === 0}
		<div class="rounded-lg border bg-card px-2 py-8 text-center text-muted-foreground">
			Нет данных для отображения по выбранным фильтрам
		</div>
	{:else}
		{#each clusters as clusterData (clusterData.cluster_id)}
			<Article cluster={clusterData} />
		{/each}
	{/if}
</div>
