<script lang="ts">
	import * as Card from '$lib/components/ui/shadcn/card';
	import * as Chart from '$lib/components/ui/shadcn/chart/index.js';
	import { BarChart } from 'layerchart';
	import { scaleBand } from 'd3-scale';

	let {
		chartData,
		minMlScoreStr
	}: {
		chartData: any[];
		minMlScoreStr: string;
	} = $props();

	const chartConfig = {
		positive: { label: 'Позитив', color: 'var(--chart-2)' },
		neutral: { label: 'Нейтрально', color: 'var(--color-muted-foreground)' },
		negative: { label: 'Негатив', color: 'var(--color-destructive)' }
	} satisfies Chart.ChartConfig;
</script>

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
