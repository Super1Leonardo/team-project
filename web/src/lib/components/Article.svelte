<script lang="ts">
	import { page as pageState } from '$app/state';
	import { goto } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { Badge } from '$lib/components/ui/shadcn/badge';
	import { Button } from '$lib/components/ui/shadcn/button';
	import {
		Card,
		CardContent,
		CardFooter,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/shadcn/card';
	import {
		Collapsible,
		CollapsibleContent,
		CollapsibleTrigger
	} from '$lib/components/ui/shadcn/collapsible';
	import * as Dialog from '$lib/components/ui/shadcn/dialog';
	import * as Tooltip from '$lib/components/ui/shadcn/tooltip';
	import type { Mention, MentionCluster, SentimentLabel } from '$lib/types/brandradar';
	import { tSentiment } from '$lib/utils';
	import { ChevronDown, ExternalLink, Loader2, Check, CheckCircle2 } from '@lucide/svelte';

	type DuplicateMention = Pick<
		Mention,
		'id' | 'source_type' | 'title' | 'text' | 'published_at' | 'relevance_score' | 'url'
	>;

	let { cluster }: { cluster: MentionCluster } = $props();

	const MOSCOW_OFFSET_MS = 3 * 60 * 60 * 1000;

	let isOpen = $state(false);
	let dialogOpen = $state(false);
	let duplicates = $state<DuplicateMention[]>([]);
	let duplicatesError = $state<string | null>(null);
	let isLoadingDuplicates = $state(false);
	let duplicatesLoadAttempted = $state(false);
	let isResolving = $state(false);

	const sentimentColor = $derived(
		cluster.sentiment_label === 'negative'
			? 'bg-red-100 border-red-500 text-red-800'
			: cluster.sentiment_label === 'positive'
				? 'bg-green-100 border-green-500 text-green-800'
				: 'bg-gray-100 border-gray-500 text-gray-800'
	);

	const relevancePercent = $derived((cluster.relevance_score * 100).toFixed(0));

	$effect(() => {
		if (isOpen && !duplicatesLoadAttempted && !isLoadingDuplicates) {
			void loadDuplicates();
		}
	});

	function toMoscowDate(value: string): Date | null {
		const date = new Date(value);
		if (Number.isNaN(date.getTime())) {
			return null;
		}

		return new Date(date.getTime() + MOSCOW_OFFSET_MS);
	}

	function padTwo(value: number): string {
		return String(value).padStart(2, '0');
	}

	function formatTime(value: string): string {
		const date = toMoscowDate(value);
		if (!date) {
			return '--:--';
		}

		return `${padTwo(date.getUTCHours())}:${padTwo(date.getUTCMinutes())}`;
	}

	function formatDateTime(value: string): string {
		const date = toMoscowDate(value);
		if (!date) {
			return '--';
		}

		return `${padTwo(date.getUTCDate())}.${padTwo(date.getUTCMonth() + 1)}.${date.getUTCFullYear()} ${padTwo(date.getUTCHours())}:${padTwo(date.getUTCMinutes())}`;
	}

	async function loadDuplicates() {
		if (!cluster.dedup_group_id) {
			duplicates = [];
			duplicatesLoadAttempted = true;
			return;
		}

		isLoadingDuplicates = true;
		duplicatesLoadAttempted = true;
		duplicatesError = null;

		try {
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

			const response = await api.get<DuplicateMention[]>(
				`/api/projects/${cluster.project_id}/mentions?${searchParams.toString()}`
			);

			if (response.error) {
				throw new Error(response.error.message || 'Failed to fetch duplicates');
			}

			duplicates = (response.data || []).filter(
				(item) => item.id !== cluster.representative_mention_id
			);
		} catch (error) {
			duplicates = [];
			duplicatesError =
				error instanceof Error ? error.message : 'Не удалось загрузить похожие публикации';
			console.error('Error fetching duplicates:', error);
		} finally {
			isLoadingDuplicates = false;
		}
	}

	async function toggleResolved() {
		if (isResolving) return;
		
		const newResolvedState = !cluster.resolved;
		isResolving = true;
		
		try {
			const response = await api.post<{ resolved: boolean }>(
				`/api/projects/${cluster.project_id}/mentions/${cluster.representative_mention_id}/resolved`,
				{ resolved: newResolvedState }
			);
			
			if (response.error) {
				console.error('Failed to update resolved status:', response.error.message);
			} else {
				cluster.resolved = newResolvedState;
				goto(pageState.url, { invalidateAll: true });
			}
		} catch (error) {
			console.error('Error updating resolved status:', error);
		} finally {
			isResolving = false;
		}
	}
</script>

<Card class={['mb-4', cluster.has_risk_words && 'shadow-xl shadow-destructive/25']}>
	<CardHeader class="flex flex-col gap-2 pb-2 sm:flex-row sm:items-start sm:justify-between">
		<div class="flex flex-col">
			<span class="text-xs text-muted-foreground sm:text-sm">
				{cluster.source_type} • {formatTime(cluster.published_at)}
			</span>

			{#if cluster.title}
				<CardTitle class="mt-1.5 text-base leading-tight sm:text-lg">{cluster.title}</CardTitle>
			{/if}
		</div>

		<div class="flex flex-wrap items-center gap-2 sm:-mt-1.5 sm:justify-end">
			<Tooltip.Root>
				<Tooltip.Trigger>
					<Badge class={sentimentColor} variant="outline">
						{tSentiment(cluster.sentiment_label as SentimentLabel)}
					</Badge>
				</Tooltip.Trigger>
				<Tooltip.Content>Тональность статьи</Tooltip.Content>
			</Tooltip.Root>

			<Tooltip.Root>
				<Tooltip.Trigger>
					<Badge variant="secondary" class="font-mono">
						{relevancePercent}%
					</Badge>
				</Tooltip.Trigger>
				<Tooltip.Content>Релевантность статьи</Tooltip.Content>
			</Tooltip.Root>

			{#if cluster.resolved}
				<Tooltip.Root>
					<Tooltip.Trigger>
						<Badge
							variant="outline"
							class="flex h-5 w-5 cursor-help items-center justify-center border-green-500 bg-green-100 p-0 text-lg font-bold text-green-600 shadow shadow-green-500/20"
						>
							<Check class="h-3 w-3" />
						</Badge>
					</Tooltip.Trigger>
					<Tooltip.Content>Обработано</Tooltip.Content>
				</Tooltip.Root>
			{:else if cluster.has_risk_words}
				<Tooltip.Root>
					<Tooltip.Trigger>
						<Badge
							variant="outline"
							class="flex h-5 w-5 cursor-help items-center justify-center border-red-500 bg-red-100 p-0 text-lg font-bold text-red-600 shadow shadow-destructive/20"
						>
							!
						</Badge>
					</Tooltip.Trigger>
					<Tooltip.Content>Статья содержит risk-слова бренда</Tooltip.Content>
				</Tooltip.Root>
			{/if}
		</div>
	</CardHeader>

	<CardContent class="pt-2 sm:pt-0">
		<p class="line-clamp-4 whitespace-pre-wrap sm:line-clamp-3 {!cluster.title ? 'text-lg' : ''}">
			{cluster.text}
		</p>

		<div class="flex w-full items-center justify-start gap-2">
			{#if cluster.has_risk_words || cluster.resolved}
				<Button
					variant={cluster.resolved ? 'outline' : 'default'}
					size="sm"
					disabled={isResolving}
					onclick={() => toggleResolved()}
					class="mt-2"
				>
					{#if isResolving}
						<Loader2 class="mr-2 h-4 w-4 animate-spin" />
					{:else}
						<CheckCircle2 class="mr-2 h-4 w-4" />
					{/if}
					{cluster.resolved ? 'Необработанное' : 'Обработано'}
				</Button>
			{/if}

			<Dialog.Root bind:open={dialogOpen}>
				<Dialog.Trigger>
					<Button
						variant="ghost"
						size="sm"
						class="mt-2 justify-start gap-1 text-muted-foreground hover:bg-transparent hover:text-foreground"
					>
						Читать далее <ExternalLink class="h-4 w-4" />
					</Button>
				</Dialog.Trigger>
				<Dialog.Content
					class="max-h-[80vh] w-full overflow-y-auto sm:max-w-3xl"
					onOpenAutoFocus={(event) => event.preventDefault()}
				>
					<Dialog.Header>
						<Dialog.Title class="text-2xl">{cluster.title || 'Публикация'}</Dialog.Title>
						<Dialog.Description>
							{cluster.source_type} • {formatDateTime(cluster.published_at)}
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
							<span>Ещё {cluster.mentions_count - 1} источника</span>
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
							<span class="ml-2 text-sm">Загрузка дублей...</span>
						</div>
					{:else if duplicatesError}
						<div
							class="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
						>
							{duplicatesError}
						</div>
					{:else if duplicates.length === 0}
						<div class="p-3 text-sm text-muted-foreground">Похожие публикации не найдены.</div>
					{:else}
						<ul class="max-h-80 mb-2 overflow-auto">
							{#each duplicates as dup (dup.id)}
								<li class="flex flex-col gap-1 border-l-2 border-muted pl-4">
									<div class="flex items-center justify-between gap-3">
										<span class="text-sm font-medium">
											{dup.source_type}
											{#if dup.url}
												<a
													href={dup.url}
													target="_blank"
													rel="noopener noreferrer"
													class="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
												>
													Оригинал <ExternalLink class="h-3 w-3" />
												</a>
											{/if}
										</span>
										<span class="text-xs text-muted-foreground">
											{formatTime(dup.published_at)}
										</span>
									</div>
									<p class="line-clamp-1 text-sm text-muted-foreground">{dup.title || dup.text}</p>
									<div class="mt-1 flex items-center gap-2">
										<span class="font-mono text-xs text-muted-foreground">
											{(dup.relevance_score * 100).toFixed(0)}%
										</span>
									</div>
								</li>
							{/each}
						</ul>
					{/if}
				</CollapsibleContent>
			</Collapsible>
		</CardFooter>
	{/if}
</Card>
