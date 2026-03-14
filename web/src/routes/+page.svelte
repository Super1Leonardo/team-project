<script lang="ts">
	import ArticleList from '$lib/components/ArticleList.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let clusters = $derived(data.clusters);
</script>

<div class="container mx-auto max-w-3xl py-8">
	<h1 class="mb-6 text-2xl font-bold">Лента упоминаний</h1>

	<ArticleList {clusters} />
</div>
