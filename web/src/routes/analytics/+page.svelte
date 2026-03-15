<script lang="ts">
	import * as Card from '$lib/components/ui/shadcn/card';
	import Heading from '$lib/components/ui/Heading.svelte';
	import TimelineChart from '$lib/components/TimelineChart.svelte';
	import FilterBar from '$lib/components/FilterBar.svelte';
	import { minMlScore, timeframe } from '$lib/stores/filters';

	let { data } = $props();

	let minMlScoreValue = $derived(parseFloat($minMlScore));

	let chartData = $derived(
		data.timeline.map((day: any) => {
			if (day.mlConfidence >= minMlScoreValue) {
				return day;
			}
			return {
				...day,
				positive: 0,
				negative: 0,
				neutral: 0
			};
		})
	);

	let hasNoTimelineData = $derived(data.timeline.length === 0);
	let hasNoFilteredData = $derived(chartData.length === 0 && data.timeline.length > 0);
</script>

<div
	class="container mx-auto flex max-w-6xl animate-in flex-col gap-6 pt-4 pb-6 duration-500 fade-in"
>
	<Heading>Аналитика репутации</Heading>

	<FilterBar />

{#if hasNoTimelineData}
	<div class="text-center text-muted-foreground py-8">
		Нет данных для отображения
	</div>
{:else}
	<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
		<Card.Root>
			<Card.Header class="pb-2">
				<Card.Title class="text-sm font-medium text-muted-foreground"
					>Обработано упоминаний</Card.Title
				>
			</Card.Header>
			<Card.Content>
				<div class="text-2xl font-bold">{data.kpi.total}</div>
				<p class="text-xs text-muted-foreground">После строгой дедупликации</p>
			</Card.Content>
		</Card.Root>

		<Card.Root>
			<Card.Header class="pb-6">
				<Card.Title class="text-sm font-medium text-muted-foreground">Spike-алерты</Card.Title>
			</Card.Header>
			<Card.Content>
				<div class="text-2xl font-bold text-destructive">{data.kpi.spikeAlerts}</div>
				<p class="text-xs text-muted-foreground">Всплески негатива за период</p>
			</Card.Content>
		</Card.Root>

		<Card.Root>
			<Card.Header class="pb-6">
				<Card.Title class="text-sm font-medium text-muted-foreground">Средний ML Score</Card.Title>
			</Card.Header>
			<Card.Content>
				<div class="text-2xl font-bold text-chart-2">{data.kpi.avgMlScore}%</div>
				<p class="text-xs text-muted-foreground">Уверенность классификатора</p>
			</Card.Content>
		</Card.Root>
	</div>

	{#if hasNoFilteredData}
		<div class="text-center text-muted-foreground py-8">
			Нет статистики по выбранным фильтрам
		</div>
	{:else}
		<TimelineChart {chartData} minMlScoreStr={$minMlScore} />
	{/if}
{/if}
</div>
