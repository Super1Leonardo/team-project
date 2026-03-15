<script lang="ts">
	import Heading from '$lib/components/ui/Heading.svelte';
	import ArticleList from '$lib/components/ArticleList.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let clusters = $derived(data.clusters);
</script>

<div class="container mx-auto max-w-3xl py-4">
	<Heading>Лента упоминаний</Heading>

	<ArticleList {clusters} />
</div>
