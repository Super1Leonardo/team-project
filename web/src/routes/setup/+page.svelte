<script lang="ts">
	import { enhance } from '$app/forms';
	import { beforeNavigate } from '$app/navigation';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Heading from '$lib/components/ui/Heading.svelte';
	import { Button } from '$lib/components/ui/shadcn/button';
	import WordList from '$lib/components/WordList.svelte';
	import { Slider } from '$lib/components/ui/shadcn/slider';
	import { Loader2 } from '@lucide/svelte';

	let { data } = $props();

	type ProjectData = typeof data.project;

	const project = $derived(data.project);

	let keywords = $state([...(data.project?.keywords ?? [])]);
	let excludeKeywords = $state([...(data.project?.exclude_keywords ?? [])]);
	let riskWords = $state([...(data.project?.risk_words ?? [])]);
	let refreshInterval = $state(
		parseInt(
			(typeof localStorage !== 'undefined' ? localStorage.getItem('feedRefreshInterval') : null) ||
				'1',
			10
		)
	);

	$effect(() => {
		keywords = [...(data.project?.keywords ?? [])];
		excludeKeywords = [...(data.project?.exclude_keywords ?? [])];
		riskWords = [...(data.project?.risk_words ?? [])];
	});

	function saveRefreshInterval() {
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem('feedRefreshInterval', String(refreshInterval));
		}
	}

	$effect(() => {
		saveRefreshInterval();
	});

	let hasChanges = $derived(
		keywords.join(',') !== (project?.keywords ?? []).join(',') ||
			excludeKeywords.join(',') !== (project?.exclude_keywords ?? []).join(',') ||
			riskWords.join(',') !== (project?.risk_words ?? []).join(',')
	);

	let isSubmitting = $state(false);

	beforeNavigate((navigation) => {
		if (hasChanges) {
			if (!confirm('У вас есть несохранённые изменения. Всё равно уйти?')) {
				navigation.cancel();
			}
		}
	});
</script>

<div class="container mx-auto max-w-3xl py-4">
	<Heading>Настройки</Heading>

	<section class="mb-8">
		<form
			method="POST"
			action="?/updateProject"
			use:enhance={() => {
				isSubmitting = true;
				return async ({ result, update }) => {
					await update({ reset: false });
					isSubmitting = false;

					if (result.type === 'failure') {
						toast.error('Ошибка при сохранении настроек');
					} else if (result.type === 'success') {
						toast.success('Настройки сохранены. Изменения войдут через минуту.');

						const actionData = (result as { data: { project?: ProjectData } }).data;
						if (actionData?.project) {
							keywords = [...actionData.project.keywords];
							excludeKeywords = [...actionData.project.exclude_keywords];
							riskWords = [...actionData.project.risk_words];
						}
					}
				};
			}}
		>
			<input type="hidden" name="project_id" value={project?.id} />
			<input type="hidden" name="keywords" value={keywords.join(',')} />
			<input type="hidden" name="exclude_keywords" value={excludeKeywords.join(',')} />
			<input type="hidden" name="risk_words" value={riskWords.join(',')} />

			<div class="space-y-6">
				<WordList
					label="Ключевые слова"
					bind:words={keywords}
					description="Слова для поиска упоминаний"
				/>

				<WordList
					label="Исключающие слова"
					bind:words={excludeKeywords}
					description="Посты с этими словами будут помечены как нерелевантные"
				/>

				<WordList
					label="Слова риска"
					bind:words={riskWords}
					description="Слова, сигнализирующие о потенциальном риске"
				/>

				<Button type="submit" disabled={isSubmitting || !hasChanges} class="w-full">
					{#if isSubmitting}
						<Loader2 class="mr-2 h-4 w-4 animate-spin" />
					{/if}
					Сохранить
				</Button>

				<h2 class="text-xl font-semibold mb-0">Локальные настройки</h2>
				<p class="text-sm text-muted-foreground mb-4">
					Локальные настройки сохраняются автоматически в браузере
				</p>
				<section class="rounded-lg border bg-card p-4">
					<div class="flex flex-col gap-2">
						<div class="flex items-center gap-4">
							<label class="text-sm font-medium"> Автообновление ленты: </label>
							<Slider
								type="single"
								bind:value={refreshInterval}
								min={1}
								max={60}
								step={1}
								class="max-w-[200px]"
							/>
							<span class="text-sm text-muted-foreground">{refreshInterval} мин.</span>
						</div>
					</div>
				</section>
			</div>
		</form>
	</section>
</div>
