<script lang="ts">
	import Heading from '$lib/components/ui/Heading.svelte';
	import ArticleList from '$lib/components/ArticleList.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import { Button } from '$lib/components/ui/shadcn/button';
	import * as Pagination from '$lib/components/ui/shadcn/pagination';
	import { goto } from '$app/navigation';
	import { page as pageState } from '$app/state';
	import type { PageData } from './$types';
	import type { MentionCluster } from '$lib/types/brandradar';
	import { ChevronLeft, ChevronRight } from '@lucide/svelte';
	import { 
		notificationsEnabled, 
		notifiedCriticalIds,
		addNotifiedId,
		showCriticalArticleNotification,
		initNotifications
	} from '$lib/stores/notifications';
	import { get } from 'svelte/store';
	import { onMount } from 'svelte';

	let { data }: { data: PageData } = $props();

	let currentPage = $state(parseInt(pageState.url.searchParams.get('page') || '1'));
	let previousCriticalIds = $state<Set<number>>(new Set());

	function goToPage(newPage: number) {
		const url = new URL(pageState.url);
		if (newPage <= 1) {
			url.searchParams.delete('page');
		} else {
			url.searchParams.set('page', String(newPage));
		}
		goto(url, { invalidateAll: true });
	}

	let clusters: MentionCluster[] = $derived((data.clusters as MentionCluster[]) || []);
	const hasError = $derived(!!data.error);

	function checkForNewCriticalArticles() {
		if (!$notificationsEnabled) return;
		
		const currentCriticalIds = clusters
			.filter(c => c.has_risk_words && !c.resolved)
			.map(c => c.representative_mention_id);
		
		const newCriticalIds = currentCriticalIds.filter(
			id => !previousCriticalIds.has(id) && !get(notifiedCriticalIds).has(id)
		);
		
		for (const id of newCriticalIds) {
			const cluster = clusters.find(c => c.representative_mention_id === id);
			if (cluster) {
				const title = cluster.title || 'Новая рисковая статья';
				const preview = cluster.text?.substring(0, 100) || '';
				
				showCriticalArticleNotification(
					'⚠️ Рисковая статья',
					title + (preview ? ` - ${preview}...` : ''),
					() => {
						goto(`/?page=${currentPage}`);
					}
				);
				
				addNotifiedId(id);
			}
		}
		
		previousCriticalIds = new Set(currentCriticalIds);
	}

	$effect(() => {
		if (clusters.length > 0) {
			checkForNewCriticalArticles();
		}
	});

	onMount(() => {
		initNotifications();
		previousCriticalIds = new Set(
			clusters.filter(c => c.has_risk_words && !c.resolved).map(c => c.representative_mention_id)
		);
	});
</script>

<div class="container mx-auto max-w-3xl py-4">
	<div class="mb-6 flex w-full flex-col items-center">
		<Heading>Лента</Heading>

		<FilterBar health={data.health} />
	</div>

	{#if hasError}
		<div class="rounded-lg border border-destructive bg-destructive/10 p-6 text-center">
			<p class="mb-4 text-destructive">
				{data.error?.message || 'Произошла ошибка при загрузке данных'}
			</p>
			<Button variant="outline" onclick={() => window.location.reload()}>Повторить</Button>
		</div>
	{:else}
		<ArticleList {clusters} />

		{#if data.pagination && data.pagination.total > data.pagination.pageSize}
			{@const totalPages = Math.ceil(data.pagination.total / data.pagination.pageSize)}
			<Pagination.Root
				class="mt-4"
				count={data.pagination.total}
				perPage={data.pagination.pageSize}
				bind:page={currentPage}
				onPageChange={(newPage) => goToPage(newPage)}
			>
				{#snippet children({ pages, currentPage: cp })}
					<Pagination.Content>
						<Pagination.PrevButton onclick={() => goToPage(cp - 1)} disabled={cp <= 1}>
							<ChevronLeft class="size-6" />
						</Pagination.PrevButton>
						{#each pages as pageItem (pageItem.key)}
							{#if pageItem.type === 'ellipsis'}
								<Pagination.Ellipsis class="size-9" />
							{:else}
								<Pagination.Link class="size-9" isActive={cp === pageItem.value} page={pageItem}>
									{pageItem.value}
								</Pagination.Link>
							{/if}
						{/each}
						<Pagination.NextButton onclick={() => goToPage(cp + 1)} disabled={cp >= totalPages}>
							<ChevronRight class="size-6" />
						</Pagination.NextButton>
					</Pagination.Content>
				{/snippet}
			</Pagination.Root>
		{/if}
	{/if}
</div>
