<script lang="ts">
	import * as Card from '$lib/components/ui/shadcn/card';
	import * as Select from '$lib/components/ui/shadcn/select';
	import Heading from '$lib/components/ui/Heading.svelte';
	import * as Chart from '$lib/components/ui/shadcn/chart/index.js';
	import { scaleBand } from 'd3-scale';
	import { BarChart } from 'layerchart';

	let { data } = $props();

	const chartConfig = {
		positive: { label: 'Позитив', color: 'var(--chart-2)' },
		neutral: { label: 'Нейтрально', color: 'var(--color-muted-foreground)' },
		negative: { label: 'Негатив', color: 'var(--color-destructive)' }
	} satisfies Chart.ChartConfig;

	let timeframe = $state('7d');
	let minMlScoreStr = $state('0.7');

	let minMlScore = $derived(parseFloat(minMlScoreStr));

	let chartData = $derived(data.timeline.filter((day: any) => day.mlConfidence >= minMlScore));
</script>

<div class="container mx-auto flex max-w-6xl animate-in flex-col gap-6 py-6 duration-500 fade-in">
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<Heading>Аналитика репутации</Heading>

		<div class="flex flex-wrap gap-4">
			<Select.Root type="single" bind:value={minMlScoreStr}>
				<Select.Trigger class="w-50">
					ML Уверенность: &ge; {minMlScoreStr}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value="0.5">&ge; 0.5 (Все данные)</Select.Item>
					<Select.Item value="0.7">&ge; 0.7 (Базовая норма)</Select.Item>
					<Select.Item value="0.9">&ge; 0.9 (Высокая точность)</Select.Item>
				</Select.Content>
			</Select.Root>

			<Select.Root type="single" bind:value={timeframe}>
				<Select.Trigger class="w-40">
					Период: {timeframe}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value="24h">За 24 часа</Select.Item>
					<Select.Item value="7d">За 7 дней</Select.Item>
					<Select.Item value="30d">За 30 дней</Select.Item>
				</Select.Content>
			</Select.Root>
		</div>
	</div>

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
			<Card.Header class="pb-2">
				<Card.Title class="text-sm font-medium text-muted-foreground">Spike-алерты</Card.Title>
			</Card.Header>
			<Card.Content>
				<div class="text-2xl font-bold text-destructive">{data.kpi.spikeAlerts}</div>
				<p class="text-xs text-muted-foreground">Всплески негатива за период</p>
			</Card.Content>
		</Card.Root>

		<Card.Root>
			<Card.Header class="pb-2">
				<Card.Title class="text-sm font-medium text-muted-foreground">Средний ML Score</Card.Title>
			</Card.Header>
			<Card.Content>
				<div class="text-2xl font-bold text-chart-2">{data.kpi.avgMlScore}%</div>
				<p class="text-xs text-muted-foreground">Уверенность классификатора</p>
			</Card.Content>
		</Card.Root>
	</div>

	<Card.Root class="col-span-3">
		<Card.Header>
			<Card.Title>Динамика тональности</Card.Title>
			<Card.Description>
				Распределение упоминаний по дням. Данные с ML Score &ge; {minMlScoreStr}
			</Card.Description>
		</Card.Header>
		<Card.Content>
			<div class="h-87.5 w-full">
				<Chart.Container config={chartConfig} class="h-full w-full">
					<BarChart
						data={chartData}
						xScale={scaleBand().padding(0.25)}
						x="date"
						axis="x"
						seriesLayout="group"
						legend
						series={[
							{ key: 'positive', color: chartConfig.positive.color },
							{ key: 'neutral', color: chartConfig.neutral.color },
							{ key: 'negative', color: chartConfig.negative.color }
						]}
						props={{
							xAxis: { format: (d: string) => d.slice(5) },
							bars: { radius: 4, stroke: 'none' }
						}}
					>
						{#snippet tooltip()}
							<Chart.Tooltip />
						{/snippet}
					</BarChart>
				</Chart.Container>
			</div>
		</Card.Content>
	</Card.Root>
</div>
