<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import * as Select from '$lib/components/ui/shadcn/select';
	import { confidence, period, sentiment } from '$lib/stores/filters';

	const DEFAULTS = {
		confidence: '0.7',
		period: '7d'
	};

	function syncFromUrl() {
		const urlConf = page.url.searchParams.get('confidence');
		const urlPeriod = page.url.searchParams.get('period');
		const urlSentiment = page.url.searchParams.get('sentiment');
		confidence.set(urlConf || DEFAULTS.confidence);
		period.set(urlPeriod || DEFAULTS.period);
		sentiment.set(urlSentiment || null);
	}

	syncFromUrl();

	function updateFilter(key: string, value: string | null) {
		const isDefault =
			(key === 'confidence' && value === DEFAULTS.confidence) ||
			(key === 'period' && value === DEFAULTS.period) ||
			(key === 'sentiment' && !value);

		const url = new URL(page.url);
		if (value && !isDefault) {
			url.searchParams.set(key, value);
		} else {
			url.searchParams.delete(key);
		}
		goto(url, { keepFocus: true, noScroll: true, invalidateAll: false });
	}

	function getSentimentLabel(value: string | null): string {
		switch (value) {
			case 'positive':
				return 'Позитивные';
			case 'neutral':
				return 'Нейтральные';
			case 'negative':
				return 'Негативные';
			default:
				return 'Все тональности';
		}
	}
</script>

<div class="flex w-full flex-wrap gap-3 rounded-lg border bg-card p-3 sm:w-fit sm:gap-4 sm:p-4">
	<div class="flex min-w-[140px] flex-col gap-1.5">
		<span class="text-xs font-medium text-muted-foreground">Тональность</span>
		<Select.Root
			type="single"
			value={$sentiment || ''}
			onValueChange={(v) => {
				const val = v === '' ? null : v;
				sentiment.set(val);
				updateFilter('sentiment', val);
			}}
		>
			<Select.Trigger class="w-full [&>span]:truncate">
				{getSentimentLabel($sentiment)}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="">Все тональности</Select.Item>
				<Select.Item value="positive">Позитивные</Select.Item>
				<Select.Item value="neutral">Нейтральные</Select.Item>
				<Select.Item value="negative">Негативные</Select.Item>
			</Select.Content>
		</Select.Root>
	</div>

	<div class="flex min-w-[120px] flex-1 flex-col gap-1.5 sm:max-w-[140px]">
		<span class="text-xs font-medium text-muted-foreground">Уверенность ML</span>
		<Select.Root
			type="single"
			value={$confidence}
			onValueChange={(v) => {
				confidence.set(v);
				updateFilter('confidence', v);
			}}
		>
			<Select.Trigger class="w-full">
				{$confidence === '0.5' ? '≥ 50%' : $confidence === '0.7' ? '≥ 70%' : '≥ 90%'}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="0.5">Средняя (≥ 50%)</Select.Item>
				<Select.Item value="0.7">Высокая (≥ 70%)</Select.Item>
				<Select.Item value="0.9">Строгая (≥ 90%)</Select.Item>
			</Select.Content>
		</Select.Root>
	</div>

	<div class="flex min-w-[140px] flex-1 flex-col gap-1.5">
		<span class="text-xs font-medium text-muted-foreground">Период анализа</span>
		<Select.Root
			type="single"
			value={$period}
			onValueChange={(v) => {
				period.set(v);
				updateFilter('period', v);
			}}
		>
			<Select.Trigger class="w-full [&>span]:truncate">
				{$period === '24h' ? 'За 24 часа' : $period === '7d' ? 'За 7 дней' : 'За 30 дней'}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="24h">Последние 24 часа</Select.Item>
				<Select.Item value="7d">Последние 7 дней</Select.Item>
				<Select.Item value="30d">Последние 30 дней</Select.Item>
			</Select.Content>
		</Select.Root>
	</div>
</div>
