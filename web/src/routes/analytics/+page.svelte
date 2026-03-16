<script lang="ts">
	import { page } from '$app/state';
	import * as Card from '$lib/components/ui/shadcn/card';
	import Heading from '$lib/components/ui/Heading.svelte';
	import TimelineChart from '$lib/components/TimelineChart.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import { Button } from '$lib/components/ui/shadcn/button';

	let { data } = $props();

	let chartData = $derived(data.timeline);
	let hasNoTimelineData = $derived(data.timeline.length === 0);
	let hasError = $derived(!!data.error);

	let currentConfidence = $derived(page.url.searchParams.get('confidence') || '0.7');
</script>

<div
	class="container mx-auto flex max-w-6xl animate-in flex-col gap-6 pt-4 pb-6 duration-500 fade-in"
>
	<div class="flex w-full flex-col items-center">
		<Heading>Аналитика репутации</Heading>

		<FilterBar />
	</div>

	{#if hasError}
		<div class="rounded-lg border border-destructive bg-destructive/10 p-6 text-center">
			<p class="mb-4 text-destructive">
				{data.error?.message || 'Произошла ошибка при загрузке данных'}
			</p>
			<Button variant="outline" onclick={() => window.location.reload()}>Повторить</Button>
		</div>
	{:else if hasNoTimelineData}
		<div class="rounded-lg border bg-card py-8 px-2 text-center text-muted-foreground">
			Нет данных для отображения по выбранным фильтрам
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
			<Card.Root>
				<Card.Header class="pb-4">
					<Card.Title class="text-sm font-medium text-muted-foreground"
						>Обработано упоминаний</Card.Title
					>
				</Card.Header>
				<Card.Content>
					<div class="text-2xl font-bold">{data.kpi.total}</div>
					<p class="text-xs text-muted-foreground">За выбранный период</p>
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header class="pb-4">
					<Card.Title class="text-sm font-medium text-muted-foreground">Spike-алерты</Card.Title>
				</Card.Header>
				<Card.Content>
					<div class="text-2xl font-bold text-destructive">{data.kpi.spikeAlerts}</div>
					<p class="text-xs text-muted-foreground">Всплески негатива</p>
				</Card.Content>
			</Card.Root>

			<Card.Root>
				<Card.Header class="pb-4">
					<Card.Title class="text-sm font-medium text-muted-foreground"
						>Средняя уверенность (ML Score)</Card.Title
					>
				</Card.Header>
				<Card.Content>
					<div class="text-2xl font-bold text-chart-2">{data.kpi.avgMlScore}%</div>
					<p class="text-xs text-muted-foreground">По релевантным публикациям</p>
				</Card.Content>
			</Card.Root>
		</div>

		<TimelineChart {chartData} minMlScoreStr={currentConfidence} />
	{/if}
</div>
