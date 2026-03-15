<script lang="ts">
	import { enhance } from '$app/forms';
	import { toast } from 'svelte-sonner';
	import Heading from '$lib/components/ui/Heading.svelte';
	import { Button } from '$lib/components/ui/shadcn/button';
	import WordList from '$lib/components/WordList.svelte';
	import { Loader2 } from '@lucide/svelte';

	let { data } = $props();

	type ProjectData = typeof data.project;

	let keywords = $state([...data.project.keywords]);
	let excludeKeywords = $state([...data.project.exclude_keywords]);
	let riskWords = $state([...data.project.risk_words]);

	$effect(() => {
		keywords = [...data.project.keywords];
		excludeKeywords = [...data.project.exclude_keywords];
		riskWords = [...data.project.risk_words];
	});

	let hasChanges = $derived(
		keywords.join(',') !== data.project.keywords.join(',') ||
			excludeKeywords.join(',') !== data.project.exclude_keywords.join(',') ||
			riskWords.join(',') !== data.project.risk_words.join(',')
	);

	let isSubmitting = $state(false);
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

					if (result.type === 'success') {
						toast.success('Настройки сохранены');

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
			<input type="hidden" name="keywords" value={keywords.join(',')} />
			<input type="hidden" name="exclude_keywords" value={excludeKeywords.join(',')} />
			<input type="hidden" name="risk_words" value={riskWords.join(',')} />

			<div class="space-y-6">
				<WordList
					label="Ключевые слова"
					placeholder="Введите слово и нажмите Enter"
					bind:words={keywords}
					description="Слова для поиска упоминаний"
				/>

				<WordList
					label="Исключающие слова"
					placeholder="Введите слово и нажмите Enter"
					bind:words={excludeKeywords}
					description="Посты с этими словами будут помечены как нерелевантные"
				/>

				<WordList
					label="Слова риска"
					placeholder="Введите слово и нажмите Enter"
					bind:words={riskWords}
					description="Слова, сигнализирующие о потенциальном риске"
				/>

				<Button type="submit" disabled={isSubmitting || !hasChanges}>
					{#if isSubmitting}
						<Loader2 class="mr-2 h-4 w-4 animate-spin" />
					{/if}
					Сохранить
				</Button>
			</div>
		</form>
	</section>
</div>
