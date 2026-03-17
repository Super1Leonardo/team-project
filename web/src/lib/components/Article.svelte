<script lang="ts">
	import {
		Card,
		CardContent,
		CardFooter,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/shadcn/card';
	import { Badge } from '$lib/components/ui/shadcn/badge';
	import {
		Collapsible,
		CollapsibleContent,
		CollapsibleTrigger
	} from '$lib/components/ui/shadcn/collapsible';
	import { Button } from '$lib/components/ui/shadcn/button';
	import {
		HoverCard,
		HoverCardContent,
		HoverCardTrigger
	} from '$lib/components/ui/shadcn/hover-card';
	import * as Dialog from '$lib/components/ui/shadcn/dialog';
	import { ChevronDown, ExternalLink, Loader2 } from '@lucide/svelte';
	import { page as pageState } from '$app/state';
	import { tSentiment, type SentimentLabel } from '$lib/utils';

	// Принимаем MentionClusterResponse из API
	let { cluster }: { cluster: any } = $props();

	let isOpen = $state(false);
	let dialogOpen = $state(false);

	// Стейты для ленивой загрузки дубликатов
	let duplicates = $state<any[]>([]);
	let isLoadingDuplicates = $state(false);

	let sentimentColor = $derived(
		cluster.sentiment_label === 'negative'
			? 'bg-red-100 border-red-500 text-red-800'
			: cluster.sentiment_label === 'positive'
				? 'bg-green-100 border-green-500 text-green-800'
				: 'bg-gray-100 border-gray-500 text-gray-800'
	);

	let relevancePercent = $derived((cluster.relevance_score * 100).toFixed(0));

	// Реактивно следим за открытием аккордеона для подгрузки данных
	$effect(() => {
		if (isOpen && duplicates.length === 0 && !isLoadingDuplicates) {
			loadDuplicates();
		}
	});

	async function loadDuplicates() {
		isLoadingDuplicates = true;
		try {
			// Вызываем общий эндпоинт ленты, выключая primary_only,
			// чтобы достать все посты этой дедуп-группы
			// TODO: В openapi нужно добавить параметр dedup_group_id в query для GET /mentions
			const searchParams = new URLSearchParams();
			searchParams.set('primary_only', 'false');
			searchParams.set('relevant_only', 'true');
			searchParams.set('include_total', 'false');
			searchParams.set('limit', '100');
			searchParams.set('dedup_group_id', String(cluster.dedup_group_id));

			const confidence = pageState.url.searchParams.get('confidence');
			const period = pageState.url.searchParams.get('period');
			const sentiment = pageState.url.searchParams.get('sentiment');

			if (confidence) searchParams.set('confidence', confidence);
			if (period) searchParams.set('period', period);
			if (sentiment) searchParams.set('sentiment', sentiment);

			const url = `/api/projects/${cluster.project_id}/mentions?${searchParams.toString()}`;
			const res = await fetch(url);
			if (!res.ok) throw new Error('Failed to fetch duplicates');

			const json = await res.json();
			// Исключаем основной репрезентативный пост из списка дублей
			duplicates = (json.data || []).filter((m: any) => m.id !== cluster.representative_mention_id);
		} catch (error) {
			console.error('Error fetching duplicates:', error);
		} finally {
			isLoadingDuplicates = false;
		}
	}
</script>

<Card class={['mb-4', cluster.has_risk_words && 'shadow-xl shadow-destructive/25']}>
	<CardHeader class="flex flex-col gap-2 pb-2 sm:flex-row sm:items-start sm:justify-between">
		<div class="flex flex-col">
			<span class="text-xs text-muted-foreground sm:text-sm">
				{cluster.source_type} • {new Date(cluster.published_at).toLocaleTimeString([], {
					hour: '2-digit',
					minute: '2-digit'
				})}
			</span>

			{#if cluster.title}
				<CardTitle class="mt-1.5 text-base leading-tight sm:text-lg">{cluster.title}</CardTitle>
			{/if}
		</div>

		<div class="flex flex-wrap items-center gap-2 sm:-mt-1.5 sm:justify-end">
			<HoverCard>
				<HoverCardTrigger>
					<Badge class={sentimentColor} variant="outline">
						{tSentiment(cluster.sentiment_label as SentimentLabel)}
					</Badge>
				</HoverCardTrigger>
				<HoverCardContent class="w-64 text-sm">
					<p>Тональность статьи: {cluster.sentiment_score.toFixed(2)}</p>
				</HoverCardContent>
			</HoverCard>

			<HoverCard>
				<HoverCardTrigger>
					<Badge variant="secondary" class="font-mono">
						{relevancePercent}%
					</Badge>
				</HoverCardTrigger>
				<HoverCardContent class="w-64 text-sm">
					<p>Релевантность статьи: {cluster.relevance_score.toFixed(2)}</p>
				</HoverCardContent>
			</HoverCard>

			{#if cluster.has_risk_words}
				<HoverCard>
					<HoverCardTrigger>
						<Badge
							variant="outline"
							class="flex h-5 w-5 cursor-help items-center justify-center border-red-500 bg-red-100 p-0 text-lg font-bold text-red-600 shadow shadow-destructive/20"
						>
							!
						</Badge>
					</HoverCardTrigger>
					<HoverCardContent class="w-64 text-sm">
						<p class="font-semibold">Статья содержит risk-слова бренда</p>
					</HoverCardContent>
				</HoverCard>
			{/if}
		</div>
	</CardHeader>

	<CardContent class="pt-2 sm:pt-0">
		<p class="line-clamp-4 whitespace-pre-wrap sm:line-clamp-3 {!cluster.title ? 'text-lg' : ''}">
			{cluster.text}
		</p>

		<div class="flex w-full justify-start sm:justify-end">
			<Dialog.Root bind:open={dialogOpen}>
				<Dialog.Trigger>
					<Button
						variant="ghost"
						size="sm"
						class="mt-2 w-full justify-start gap-1 px-0 text-muted-foreground hover:bg-transparent hover:text-foreground sm:justify-end"
					>
						Читать далее <ExternalLink class="h-4 w-4" />
					</Button>
				</Dialog.Trigger>
				<Dialog.Content
					class="max-h-[80vh] w-full overflow-y-auto sm:max-w-3xl"
					onOpenAutoFocus={(e) => e.preventDefault()}
				>
					<Dialog.Header>
						<Dialog.Title class="text-2xl">{cluster.title || 'Публикация'}</Dialog.Title>
						<Dialog.Description>
							{cluster.source_type} • {new Date(cluster.published_at).toLocaleString('ru-RU')}
						</Dialog.Description>
					</Dialog.Header>

					<div class="space-y-4">
						<p class="whitespace-pre-wrap">{cluster.text}</p>

						{#if cluster.url}
							<a
								href={cluster.url}
								target="_blank"
								rel="noopener noreferrer"
								class="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
							>
								Открыть оригинал <ExternalLink class="h-4 w-4" />
							</a>
						{/if}
					</div>
				</Dialog.Content>
			</Dialog.Root>
		</div>
	</CardContent>

	{#if cluster.mentions_count > 1}
		<CardFooter class="pt-0">
			<Collapsible bind:open={isOpen} class="w-full">
				<CollapsibleTrigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							class="flex h-8 w-full justify-between p-0 text-muted-foreground hover:bg-transparent"
						>
							<span>Ещё {cluster.mentions_count - 1} источника ▸</span>
							<ChevronDown
								size={16}
								class="transition-transform duration-200 {isOpen ? 'rotate-180' : ''}"
							/>
						</Button>
					{/snippet}
				</CollapsibleTrigger>

				<CollapsibleContent class="space-y-3 pt-4">
					{#if isLoadingDuplicates}
						<div class="flex items-center justify-center p-4 text-muted-foreground">
							<Loader2 class="h-5 w-5 animate-spin" />
							<span class="ml-2 text-sm">Загрузка дубликатов...</span>
						</div>
					{:else}
						{#each duplicates as dup (dup.id)}
							<div class="flex flex-col gap-1 border-l-2 border-muted pl-4">
								<div class="flex items-center justify-between">
									<span class="text-sm font-medium">{dup.source_type}</span>
									<span class="text-xs text-muted-foreground">
										{new Date(dup.published_at).toLocaleTimeString([], {
											hour: '2-digit',
											minute: '2-digit'
										})}
									</span>
								</div>
								<p class="line-clamp-1 text-sm text-muted-foreground">{dup.title || dup.text}</p>
								<div class="mt-1 flex items-center gap-2">
									<span class="font-mono text-xs text-muted-foreground">
										{(dup.relevance_score * 100).toFixed(0)}%
									</span>
								</div>
							</div>
						{/each}
					{/if}
				</CollapsibleContent>
			</Collapsible>
		</CardFooter>
	{/if}
</Card>
