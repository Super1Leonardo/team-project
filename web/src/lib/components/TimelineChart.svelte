<script lang="ts">
	import * as Card from '$lib/components/ui/shadcn/card';
	import * as Chart from '$lib/components/ui/shadcn/chart/index.js';
	import { BarChart } from 'layerchart';
	import { scaleBand } from 'd3-scale';

	let {
		chartData
	}: {
		chartData: any[];
	} = $props();

	// Уходим от зарезервированного слова 'negative' в ключах
	const chartConfig = {
		pos: { label: 'Позитив', color: 'var(--chart-2)' },
		neu: { label: 'Нейтрально', color: 'var(--color-muted-foreground)' },
		neg: { label: 'Негатив', color: 'var(--color-destructive)' }
	} satisfies Chart.ChartConfig;
</script>

<Card.Root class="col-span-3">
	<Card.Header>
		<Card.Title>Динамика тональности</Card.Title>
		<Card.Description>Распределение релевантных упоминаний по дням</Card.Description>
	</Card.Header>
	<Card.Content>
		<div class="h-87.5 w-full">
			<Chart.Container config={chartConfig} class="h-full w-full">
				<BarChart
					data={chartData}
					xScale={scaleBand().padding(0.25)}
					x="date"
					axis="x"
					seriesLayout="stack"
					legend
					series={[
						{ key: 'pos', color: chartConfig.pos.color },
						{ key: 'neu', color: chartConfig.neu.color },
						{ key: 'neg', color: chartConfig.neg.color }
					]}
					props={{
						xAxis: { format: (d: string) => d.slice(5) },
						bars: { stroke: 'none' }
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
