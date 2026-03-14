<script lang="ts">
	import ArticleList from '$lib/components/ArticleList.svelte';
	import type { PageData } from './$types';

	// Принимаем данные от сервера
	let { data }: { data: PageData } = $props();

	// Оборачиваем в состояние для будущих фильтров
	let clusters = $state(data.clusters);
</script>

<div class="container mx-auto max-w-3xl py-8">
	<h1 class="mb-6 text-2xl font-bold">Лента упоминаний</h1>

	<ArticleList {clusters} />
</div>
