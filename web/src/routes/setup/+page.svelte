<script lang="ts">
	import { enhance } from '$app/forms';
	import { toast } from 'svelte-sonner';
	import Heading from '$lib/components/ui/Heading.svelte';
	import { Input } from '$lib/components/ui/shadcn/input';
	import { Label } from '$lib/components/ui/shadcn/label';
	import { Switch } from '$lib/components/ui/shadcn/switch';
	import { Button } from '$lib/components/ui/shadcn/button';
	import * as Dialog from '$lib/components/ui/shadcn/dialog';
	import { Separator } from '$lib/components/ui/shadcn/separator';
	import WordList from '$lib/components/WordList.svelte';
	import { Send, MessageCircle, Radio, Trash2, Plus, Loader2 } from '@lucide/svelte';
	import type { Source } from './+page.server';

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

	let addDialogOpen = $state(false);
	let selectedSourceType = $state<Source['source_type']>('telegram');
	let newChannel = $state('');
	let newGroupId = $state('');
	let newDomain = $state('');
	let newFeedUrl = $state('');
	let isSubmitting = $state(false);

	function resetAddForm() {
		newChannel = '';
		newGroupId = '';
		newDomain = '';
		newFeedUrl = '';
	}

	let canAddSource = $derived.by(() => {
		if (selectedSourceType === 'telegram') {
			return newChannel.trim().length > 0;
		}
		if (selectedSourceType === 'vk') {
			return newGroupId.trim().length > 0;
		}
		if (selectedSourceType === 'rss') {
			return newFeedUrl.trim().length > 0;
		}
		return false;
	});

	function getSourceDisplayConfig(source: Source): string {
		if (source.source_type === 'telegram') {
			return `@${source.source_config.channel}`;
		}
		if (source.source_type === 'vk') {
			return source.source_config.domain || `ID: ${source.source_config.group_id}`;
		}
		if (source.source_type === 'rss') {
			return source.source_config.feed_url || 'No URL';
		}
		return 'Unknown';
	}

	const sourceTypeOptions = [
		{ value: 'telegram', label: 'Telegram' },
		{ value: 'vk', label: 'VK' },
		{ value: 'rss', label: 'RSS' }
	];
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

	<Separator class="my-8" />

	<section>
		<div class="flex items-center justify-between mb-4">
			<h2 class="text-xl font-semibold">Источники</h2>

			<Dialog.Root bind:open={addDialogOpen}>
					<Dialog.Trigger>
					<Button onclick={resetAddForm}>
						<Plus class="mr-2 h-4 w-4" />
						Добавить источник
					</Button>
				</Dialog.Trigger>
				<Dialog.Content>
					<Dialog.Header>
						<Dialog.Title>Добавить источник</Dialog.Title>
						<Dialog.Description>
							Выберите тип источника и заполните необходимые поля
						</Dialog.Description>
					</Dialog.Header>

					<form
						method="POST"
						action="?/addSource"
						use:enhance={() => {
							isSubmitting = true;
							return async ({ result, update }) => {
								await update();
								isSubmitting = false;
								addDialogOpen = false;
								resetAddForm();

								if (result.type === 'success') {
									toast.success('Источник добавлен');
								}
							};
						}}
					>
						<div class="space-y-4 py-4">
							<div class="space-y-2">
								<Label for="source_type">Тип источника</Label>
								<select
									id="source_type"
									name="source_type"
									class="flex h-9 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
									bind:value={selectedSourceType}
								>
									{#each sourceTypeOptions as option}
										<option value={option.value}>{option.label}</option>
									{/each}
								</select>
							</div>

							{#if selectedSourceType === 'telegram'}
								<div class="space-y-2">
									<Label for="channel">Канал</Label>
									<Input id="channel" name="channel" placeholder="banksta" bind:value={newChannel} />
									<p class="text-sm text-muted-foreground">Имя канала без @</p>
								</div>
							{:else if selectedSourceType === 'vk'}
								<div class="space-y-2">
									<Label for="group_id">ID группы</Label>
									<Input id="group_id" name="group_id" placeholder="-12345" type="number" bind:value={newGroupId} />
								</div>
								<div class="space-y-2">
									<Label for="domain">Домен (опционально)</Label>
									<Input id="domain" name="domain" placeholder="bank_news" bind:value={newDomain} />
								</div>
							{:else if selectedSourceType === 'rss'}
								<div class="space-y-2">
									<Label for="feed_url">URL ленты</Label>
									<Input
										id="feed_url"
										name="feed_url"
										placeholder="https://example.com/rss"
										type="url"
										bind:value={newFeedUrl}
									/>
								</div>
							{/if}

							<div class="space-y-2">
								<Label for="poll_interval">Интервал опроса (сек)</Label>
								<Input
									id="poll_interval"
									name="poll_interval"
									value="300"
									type="number"
									min="60"
									max="3600"
								/>
							</div>

							<Dialog.Footer>
								<Button type="button" variant="outline" onclick={() => addDialogOpen = false}>
									Отмена
								</Button>
								<Button type="submit" disabled={isSubmitting || !canAddSource}>
									{#if isSubmitting}
										<Loader2 class="mr-2 h-4 w-4 animate-spin" />
									{/if}
									Добавить
								</Button>
							</Dialog.Footer>
						</div>
					</form>
				</Dialog.Content>
			</Dialog.Root>
		</div>

		<div class="space-y-3">
			{#each data.sources as source (source.id)}
				<div class="flex items-center justify-between p-4 border rounded-lg">
					<div class="flex items-center gap-4">
						<div class="flex h-10 w-10 items-center justify-center rounded-full bg-muted">
							{#if source.source_type === 'telegram'}
								<Send class="h-5 w-5" />
							{:else if source.source_type === 'vk'}
								<MessageCircle class="h-5 w-5" />
							{:else if source.source_type === 'rss'}
								<Radio class="h-5 w-5" />
							{/if}
						</div>
						<div>
							<div class="flex items-center gap-2">
								<span class="font-medium capitalize">{source.source_type}</span>
								<span class="text-muted-foreground">{getSourceDisplayConfig(source)}</span>
							</div>
							<div class="flex items-center gap-2 text-sm text-muted-foreground">
								{#if source.last_collected_at}
									Последний сбор: {new Date(source.last_collected_at).toLocaleString('ru-RU')}
								{:else}
									Ещё не собирался
								{/if}
								{#if source.last_error}
									<span class="text-destructive">• {source.last_error}</span>
								{/if}
							</div>
						</div>
					</div>

					<div class="flex items-center gap-4">
						<form
							method="POST"
							action="?/toggleSource"
							use:enhance={() => {
								return async ({ update }) => {
									await update();
								};
							}}
						>
							<input type="hidden" name="source_id" value={source.id} />
							<Switch checked={source.is_active} />
						</form>

						<form
							method="POST"
							action="?/deleteSource"
							use:enhance={() => {
								return async ({ result, update }) => {
									await update();
									if (result.type === 'success') {
										toast.success('Источник удалён');
									}
								};
							}}
						>
							<input type="hidden" name="source_id" value={source.id} />
							<Button variant="ghost" size="icon" type="submit">
								<Trash2 class="h-4 w-4 text-destructive" />
							</Button>
						</form>
					</div>
				</div>
			{:else}
				<div
					class="flex h-32 items-center justify-center rounded-lg border border-dashed border-border text-muted-foreground"
				>
					Нет источников. Добавьте первый источник.
				</div>
			{/each}
		</div>
	</section>
</div>
