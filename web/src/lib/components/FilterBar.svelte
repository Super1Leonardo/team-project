<script lang="ts">
	import * as Select from '$lib/components/ui/shadcn/select';
	import { minMlScore, timeframe } from '$lib/stores/filters';

	let minMlScoreValue = $state('0.7');
	let timeframeValue = $state('7d');

	minMlScore.subscribe(v => minMlScoreValue = v);
	timeframe.subscribe(v => timeframeValue = v);

	function updateMinMlScore(v: string) {
		minMlScore.set(v);
	}

	function updateTimeframe(v: string) {
		timeframe.set(v);
	}
</script>

<div class="flex items-center flex-wrap gap-4">
	<div class="text-lg font-semibold">Фильтры:</div>

	<Select.Root type="single" value={minMlScoreValue} onValueChange={updateMinMlScore}>
		<Select.Trigger class="w-50">
			ML Уверенность: &ge; {minMlScoreValue}
		</Select.Trigger>
		<Select.Content>
			<Select.Item value="0.5">&ge; 0.5 (Все данные)</Select.Item>
			<Select.Item value="0.7">&ge; 0.7 (Базовая норма)</Select.Item>
			<Select.Item value="0.9">&ge; 0.9 (Высокая точность)</Select.Item>
		</Select.Content>
	</Select.Root>

	<Select.Root type="single" value={timeframeValue} onValueChange={updateTimeframe}>
		<Select.Trigger class="w-40">
			Период: {timeframeValue}
		</Select.Trigger>
		<Select.Content>
			<Select.Item value="24h">За 24 часа</Select.Item>
			<Select.Item value="7d">За 7 дней</Select.Item>
			<Select.Item value="30d">За 30 дней</Select.Item>
		</Select.Content>
	</Select.Root>
</div>
