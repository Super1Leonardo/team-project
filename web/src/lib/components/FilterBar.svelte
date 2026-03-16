<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import * as Select from '$lib/components/ui/shadcn/select';
	import { confidence, period } from '$lib/stores/filters';

	function syncFromUrl() {
		const urlConf = page.url.searchParams.get('confidence') || '0.7';
		const urlPeriod = page.url.searchParams.get('period') || '7d';
		confidence.set(urlConf);
		period.set(urlPeriod);
	}

	syncFromUrl();

	function updateFilter(key: string, value: string) {
		const url = new URL(page.url);
		url.searchParams.set(key, value);
		goto(url, { keepFocus: true, noScroll: true, invalidateAll: false });
	}
</script>

<div class="flex w-fit flex-wrap items-center gap-4 rounded-lg border bg-card p-4">
	<div class="flex flex-col gap-1.5">
		<span class="text-xs font-medium text-muted-foreground">Уверенность ML (Relevance)</span>
		<Select.Root
			type="single"
			value={$confidence}
			onValueChange={(v) => {
				confidence.set(v);
				updateFilter('confidence', v);
			}}
		>
			<Select.Trigger class="w-45">
				{$confidence === '0.5'
					? 'Средняя (≥ 50%)'
					: $confidence === '0.7'
						? 'Высокая (≥ 70%)'
						: 'Строгая (≥ 90%)'}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="0.5">Средняя (≥ 50%)</Select.Item>
				<Select.Item value="0.7">Высокая (≥ 70%)</Select.Item>
				<Select.Item value="0.9">Строгая (≥ 90%)</Select.Item>
			</Select.Content>
		</Select.Root>
	</div>

	<div class="flex flex-col gap-1.5">
		<span class="text-xs font-medium text-muted-foreground">Период анализа</span>
		<Select.Root
			type="single"
			value={$period}
			onValueChange={(v) => {
				period.set(v);
				updateFilter('period', v);
			}}
		>
			<Select.Trigger class="w-45">
				{$period === '24h'
					? 'Последние 24 часа'
					: $period === '7d'
						? 'Последние 7 дней'
						: 'Последние 30 дней'}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="24h">Последние 24 часа</Select.Item>
				<Select.Item value="7d">Последние 7 дней</Select.Item>
				<Select.Item value="30d">Последние 30 дней</Select.Item>
			</Select.Content>
		</Select.Root>
	</div>
</div>
