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
	import * as Tooltip from '$lib/components/ui/shadcn/tooltip';
	import { ChevronDown } from '@lucide/svelte';
	import { tSentiment, type SentimentLabel } from '$lib/utils';

	// Добавлена базовая типизация any (в идеале импортировать тип Cluster)
	let { cluster }: { cluster: any } = $props();

	// Svelte 5 Rune для состояния раскрытия дублей
	let isOpen = $state(false);

	// Цветовая кодировка тональности
	let sentimentColor = $derived(
		cluster.sentiment === 'negative'
			? 'bg-red-100 border-red-500 text-red-800'
			: cluster.sentiment === 'positive'
				? 'bg-green-100 border-green-500 text-green-800'
				: 'bg-gray-100 border-gray-500 text-gray-800'
	);
</script>

<Card
	data-testid="article-card"
	class={['mb-4', cluster.hasRiskWords && 'shadow-xl shadow-destructive/25']}
>
	<CardHeader class="flex flex-row items-start justify-between pb-2">
		<div>
			<CardTitle class="text-lg">{cluster.title}</CardTitle>
			<span class="text-sm text-muted-foreground"
				>{cluster.source} • {new Date(cluster.publishedAt).toLocaleTimeString()}</span
			>
		</div>

		<div class="-mt-1.5 flex items-end gap-2">
			<Badge data-testid="sentiment-badge" class={[sentimentColor]} variant="outline">
				{tSentiment(cluster.sentiment as SentimentLabel)}
			</Badge>

			<Tooltip.Root>
				<Tooltip.Trigger>
					<Badge data-testid="ml-score-badge" variant="secondary">
						{cluster.mlScore > 0 ? cluster.mlScore : '—'}%
					</Badge>
				</Tooltip.Trigger>
				<Tooltip.Content>Значение релевантности</Tooltip.Content>
			</Tooltip.Root>

			{#if cluster.hasRiskWords}
				<HoverCard>
					<HoverCardTrigger>
						<Badge
							data-testid="risk-words-alert"
							variant="outline"
							class="flex h-5.5 min-w-5.5 cursor-help gap-1 border-red-500 bg-red-100 px-1 text-lg font-bold text-red-600 shadow shadow-destructive/20"
							>!</Badge
						>
					</HoverCardTrigger>
					<HoverCardContent class="w-64 text-sm">
						<p class="font-semibold">Статья содержит критически важную информацию о бизнесе</p>
					</HoverCardContent>
				</HoverCard>
			{/if}
		</div>
	</CardHeader>

	<CardContent>
		<p class="line-clamp-3 text-sm">{cluster.text}</p>
	</CardContent>

	{#if cluster.duplicates.length > 0}
		<CardFooter class="pt-0">
			<Collapsible bind:open={isOpen} class="w-full">
				<CollapsibleTrigger>
					{#snippet child({ props })}
						<Button
							{...props}
							data-testid="duplicates-trigger"
							variant="ghost"
							class="flex h-8 w-full justify-between p-0 text-muted-foreground hover:bg-transparent"
						>
							<span>Похожие упоминания ({cluster.duplicates.length})</span>
							<ChevronDown
								size={16}
								class="transition-transform duration-200 {isOpen ? 'rotate-180' : ''}"
							/>
						</Button>
					{/snippet}
				</CollapsibleTrigger>

				<CollapsibleContent data-testid="duplicates-list" class="space-y-3 pt-4">
					{#each cluster.duplicates as dup}
						<div
							data-testid="duplicate-item"
							class="flex flex-col gap-1 border-l-2 border-muted pl-4"
						>
							<div class="flex items-center justify-between">
								<span class="text-sm font-medium">{dup.source}</span>
								<span class="text-xs text-muted-foreground"
									>{new Date(dup.publishedAt).toLocaleTimeString()}</span
								>
							</div>
							<p class="line-clamp-1 text-sm text-muted-foreground">{dup.title}</p>
							<div class="mt-1 flex items-center gap-2">
								<span class="font-mono text-xs text-muted-foreground"
									>Релевантность: {dup.mlScore > 0 ? (dup.mlScore * 100).toFixed(0) : '—'}%</span
								>
							</div>
						</div>
					{/each}
				</CollapsibleContent>
			</Collapsible>
		</CardFooter>
	{/if}
</Card>
