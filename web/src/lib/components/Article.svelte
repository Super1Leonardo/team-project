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
	import * as Dialog from '$lib/components/ui/shadcn/dialog';
	import { ChevronDown, ExternalLink } from '@lucide/svelte';
	import { tSentiment, type SentimentLabel } from '$lib/utils';
	import type { Cluster, HighlightSpan } from '$lib/components/ArticleList.svelte';

	type TextSegment = {
		text: string;
		highlighted: boolean;
		score?: number;
	};

	let { cluster }: { cluster: Cluster } = $props();

	let isOpen = $state(false);
	let dialogOpen = $state(false);

	function buildTextSegments(text: string, spans: HighlightSpan[]): TextSegment[] {
		if (!spans?.length) {
			return [{ text, highlighted: false }];
		}

		const normalizedSpans = [...spans]
			.filter((span) => span.start >= 0 && span.end > span.start && span.end <= text.length)
			.sort((left, right) => left.start - right.start || left.end - right.end);

		if (!normalizedSpans.length) {
			return [{ text, highlighted: false }];
		}

		const segments: TextSegment[] = [];
		let cursor = 0;

		for (const span of normalizedSpans) {
			if (span.start > cursor) {
				segments.push({
					text: text.slice(cursor, span.start),
					highlighted: false
				});
			}

			if (span.end <= cursor) {
				continue;
			}

			const start = Math.max(cursor, span.start);
			segments.push({
				text: text.slice(start, span.end),
				highlighted: true,
				score: span.score
			});
			cursor = span.end;
		}

		if (cursor < text.length) {
			segments.push({
				text: text.slice(cursor),
				highlighted: false
			});
		}

		return segments.filter((segment) => segment.text.length > 0);
	}

	let textSegments = $derived(buildTextSegments(cluster.text, cluster.highlightSpans));

	let sentimentColor = $derived(
		cluster.sentiment === 'negative'
			? 'bg-red-100 border-red-500 text-red-800'
			: cluster.sentiment === 'positive'
				? 'bg-green-100 border-green-500 text-green-800'
				: 'bg-gray-100 border-gray-500 text-gray-800'
	);
</script>

<Card class={['mb-4', cluster.hasRiskWords && 'shadow-xl shadow-destructive/25']}>
	<CardHeader class="flex flex-row items-start justify-between pb-2">
		<div>
			<CardTitle class="text-lg">{cluster.title}</CardTitle>
			<span class="text-sm text-muted-foreground"
				>{cluster.source} вЂў {new Date(cluster.publishedAt).toLocaleTimeString()}</span
			>
		</div>

		<div class="-mt-1.5 flex items-end gap-2">
			<Badge class={[sentimentColor]} variant="outline">
				{tSentiment(cluster.sentiment as SentimentLabel)}
			</Badge>

			<Tooltip.Root>
				<Tooltip.Trigger>
					<Badge variant="secondary">
						{cluster.mlScore > 0 ? cluster.mlScore : 'вЂ”'}%
					</Badge>
				</Tooltip.Trigger>
				<Tooltip.Content>Р—РЅР°С‡РµРЅРёРµ СЂРµР»РµРІР°РЅС‚РЅРѕСЃС‚Рё</Tooltip.Content>
			</Tooltip.Root>

			{#if cluster.hasRiskWords}
				<HoverCard>
					<HoverCardTrigger>
						<Badge
							variant="outline"
							class="flex h-5.5 min-w-5.5 cursor-help gap-1 px-1 text-lg font-bold bg-red-100 border-red-500 text-red-600 shadow-destructive/20 shadow"
							>!</Badge
						>
					</HoverCardTrigger>
					<HoverCardContent class="w-64 text-sm">
						<p class="font-semibold">РЎС‚Р°С‚СЊСЏ СЃРѕРґРµСЂР¶РёС‚ РєСЂРёС‚РёС‡РµСЃРєРё РІР°Р¶РЅСѓСЋ РёРЅС„РѕСЂРјР°С†РёСЋ Рѕ Р±РёР·РЅРµСЃРµ</p>
					</HoverCardContent>
				</HoverCard>
			{/if}
		</div>
	</CardHeader>

	<CardContent>
		<p class="line-clamp-3 text-sm">
			{#each textSegments as segment}
				{#if segment.highlighted}
					<mark
						class="rounded bg-amber-200/80 px-0.5 text-inherit"
						title={`ML importance: ${Math.round((segment.score ?? 0) * 100)}%`}
					>
						{segment.text}
					</mark>
				{:else}
					{segment.text}
				{/if}
			{/each}
		</p>

		{#if cluster.topTokens.length > 0}
			<div class="mt-3 flex flex-wrap gap-2">
				{#each cluster.topTokens.slice(0, 5) as token}
					<Badge variant="secondary" class="text-xs">
						{token.text} {Math.round(token.score * 100)}%
					</Badge>
				{/each}
			</div>
		{/if}

		<Dialog.Root bind:open={dialogOpen}>
			<Dialog.Trigger>
				<Button
					variant="ghost"
					size="sm"
					class="mt-2 w-full justify-end gap-1 px-0 text-muted-foreground hover:bg-transparent hover:text-foreground"
				>
					Р§РёС‚Р°С‚СЊ РґР°Р»РµРµ <ExternalLink class="h-4 w-4" />
				</Button>
			</Dialog.Trigger>
			<Dialog.Content class="max-w-3xl max-h-[80vh] overflow-y-auto m-2">
				<Dialog.Header>
					<Dialog.Title class="text-xl">{cluster.title}</Dialog.Title>
					<Dialog.Description>
						{cluster.source} вЂў {new Date(cluster.publishedAt).toLocaleString('ru-RU')}
					</Dialog.Description>
				</Dialog.Header>

				<div class="space-y-4">
					<div class="whitespace-pre-wrap break-words">
						{#each textSegments as segment}
							{#if segment.highlighted}
								<mark
									class="rounded bg-amber-200/80 px-0.5 text-inherit"
									title={`ML importance: ${Math.round((segment.score ?? 0) * 100)}%`}
								>
									{segment.text}
								</mark>
							{:else}
								{segment.text}
							{/if}
						{/each}
					</div>

					{#if cluster.url}
						<a
							href={cluster.url}
							target="_blank"
							rel="noopener noreferrer"
							class="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
						>
							РћС‚РєСЂС‹С‚СЊ РѕСЂРёРіРёРЅР°Р» <ExternalLink class="h-4 w-4" />
						</a>
					{/if}
				</div>
			</Dialog.Content>
		</Dialog.Root>
	</CardContent>

	{#if cluster.duplicates.length > 0}
		<CardFooter class="pt-0">
			<Collapsible bind:open={isOpen} class="w-full">
				<CollapsibleTrigger>
					{#snippet child({ props })}
						<Button
							{...props}
							variant="ghost"
							class="flex h-8 w-full justify-between p-0 text-muted-foreground hover:bg-transparent"
						>
							<span>РџРѕС…РѕР¶РёРµ СѓРїРѕРјРёРЅР°РЅРёСЏ ({cluster.duplicates.length})</span>
							<ChevronDown
								size={16}
								class="transition-transform duration-200 {isOpen ? 'rotate-180' : ''}"
							/>
						</Button>
					{/snippet}
				</CollapsibleTrigger>

				<CollapsibleContent class="space-y-3 pt-4">
					{#each cluster.duplicates as dup}
						<div class="flex flex-col gap-1 border-l-2 border-muted pl-4">
							<div class="flex items-center justify-between">
								<span class="text-sm font-medium">{dup.source}</span>
								<span class="text-xs text-muted-foreground"
									>{new Date(dup.publishedAt).toLocaleTimeString()}</span
								>
							</div>
							<p class="line-clamp-1 text-sm text-muted-foreground">{dup.title}</p>
							<div class="mt-1 flex items-center gap-2">
								<span class="font-mono text-xs text-muted-foreground"
									>Р РµР»РµРІР°РЅС‚РЅРѕСЃС‚СЊ: {dup.mlScore > 0 ? (dup.mlScore * 100).toFixed(0) : 'вЂ”'}%</span
								>
							</div>
						</div>
					{/each}
				</CollapsibleContent>
			</Collapsible>
		</CardFooter>
	{/if}
</Card>
