<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import * as Card from '$lib/components/ui/shadcn/card';
	import * as Select from '$lib/components/ui/shadcn/select';
	import Heading from '$lib/components/ui/Heading.svelte';
	import TimelineChart from '$lib/components/TimelineChart.svelte';

	let { data } = $props();

	// Читаем текущий период из URL или ставим дефолт
	let timeframe = $state(page.url.searchParams.get('period') || '7d');

	// Данные с бэка уже готовы для графика, ничего фильтровать на клиенте не нужно
	let chartData = $derived(
		data.timeline.map((day: any) => ({
			date: day.date,
			pos: day.positive,
			neu: day.neutral,
			neg: day.negative
		}))
	);

	// Функция для обновления URL при смене периода.
	// Это заставит SvelteKit перезапустить load-функцию и сходить на бэкенд за новыми данными.
	function handleTimeframeChange(newValue: string) {
		timeframe = newValue;
		const url = new URL(page.url);
		url.searchParams.set('period', newValue);
		// keepFocus оставляет фокус на селекте, noScroll предотвращает прыжок страницы вверх
		goto(url, { keepFocus: true, noScroll: true });
	}
</script>

<div class="container mx-auto flex max-w-6xl animate-in flex-col gap-6 py-6 duration-500 fade-in">
	<div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
		<Heading>Аналитика репутации</Heading>

		<div class="flex flex-wrap gap-4">
			<Select.Root type="single" value={timeframe} onValueChange={handleTimeframeChange}>
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

	<TimelineChart {chartData} />
</div>
