<script lang="ts">
	import * as Card from '$lib/components/ui/shadcn/card';
	import { BarChart } from 'layerchart'; //

	let {
		chartData,
		minMlScoreStr
	}: {
		chartData: any[];
		minMlScoreStr: string;
	} = $props();
</script>

<Card.Root class="col-span-1 md:col-span-3">
	<Card.Header>
		<Card.Title>Динамика тональности</Card.Title>
		<Card.Description>
			Распределение упоминаний по дням. Данные с ML Score &ge; {minMlScoreStr}
		</Card.Description>
	</Card.Header>
	<Card.Content>
		<div class="h-[350px] w-full">
			<BarChart
				data={chartData}
				x="date"
				series={[
					{ key: 'positive', color: 'hsl(var(--chart-2))', label: 'Позитив' },
					{ key: 'neutral', color: 'hsl(var(--muted-foreground))', label: 'Нейтрально' },
					{ key: 'negative', color: 'hsl(var(--destructive))', label: 'Негатив' }
				]}
				props={{
					bars: { radius: 4, stroke: 'none' }
				}}
			/>
		</div>
	</Card.Content>
</Card.Root>
