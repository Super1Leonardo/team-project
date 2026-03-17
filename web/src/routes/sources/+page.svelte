<script lang="ts">
	import { enhance } from '$app/forms';
	import { toast } from 'svelte-sonner';
	import Heading from '$lib/components/ui/Heading.svelte';
	import { Switch } from '$lib/components/ui/shadcn/switch';
	import Spinner from '$lib/components/ui/shadcn/spinner/spinner.svelte';
	import { Button } from '$lib/components/ui/shadcn/button';
	import {
		Send,
		Radio,
		Server,
		Database,
		BrainCircuit,
		Globe,
		ChevronDown,
		Plus,
		Trash2
	} from '@lucide/svelte';
	import {
		Collapsible,
		CollapsibleTrigger,
		CollapsibleContent
	} from '$lib/components/ui/shadcn/collapsible';
	import * as Dialog from '$lib/components/ui/shadcn/dialog';
	import {
		tSourceType,
		tSourceStatus,
		tSourceError,
		tHealthStatus,
		tDbStatus,
		type SourceType
	} from '$lib/utils';
	import { healthPollingUrgently } from '$lib/stores/healthPolling';

	let { data } = $props();

	let submittingSourceId = $state<number | null>(null);
	let statusOpen = $state(false);
	let addModalOpen = $state(false);
	let sourceType = $state<'telegram' | 'rss' | 'website'>('telegram');
	let sourceConfig = $state('');
	let pollInterval = $state(3600);
	let isSubmittingNew = $state(false);

	$effect(() => {
		healthPollingUrgently.set(statusOpen);
	});

	const project = $derived(data.project);
	const health = $derived(data.health);
	const healthStatus = $derived(health?.status ?? null);
	const collector = $derived(data.collector);
	const processingStatus = $derived(collector?.processing_status ?? null);
	const pageError = $derived(data.error);

	function getProcessingStatusColor(status: string | null): string {
		if (!status) return 'bg-yellow-500';
		switch (status) {
			case 'idle':
				return 'bg-gray-500';
			case 'processing':
				return 'bg-blue-500';
			case 'ready':
				return 'bg-green-500';
			default:
				return 'bg-yellow-500';
		}
	}

	function getProcessingStatusText(status: string | null): string {
		switch (status) {
			case 'idle':
				return 'Нет данных';
			case 'processing':
				return 'Обработка';
			case 'ready':
				return 'Простаивает';
			default:
				return 'Неизвестно';
		}
	}

	function getHealthColor(status: string | null): string {
		if (!status) return 'bg-yellow-500';
		switch (status) {
			case 'healthy':
				return 'bg-green-500';
			case 'degraded':
				return 'bg-yellow-500';
			case 'unhealthy':
				return 'bg-red-500';
			default:
				return 'bg-yellow-500';
		}
	}

	function getStatusColor(status: 'ok' | 'error' | 'stale'): string {
		switch (status) {
			case 'ok':
				return 'text-green-500';
			case 'error':
				return 'text-red-500';
			case 'stale':
				return 'text-yellow-500';
		}
	}

	function getStatusText(status: 'ok' | 'error' | 'stale'): string {
		return tSourceStatus(status);
	}

	function getSourceStatus(source: (typeof data.sources)[0]): 'ok' | 'error' | 'stale' {
		if (!source.is_active) return 'stale';
		if (source.last_error) return 'error';
		if (!source.last_collected_at) return 'stale';

		const lastCollected = new Date(source.last_collected_at);
		const now = new Date();
		const diffMinutes = (now.getTime() - lastCollected.getTime()) / (1000 * 60);

		if (diffMinutes > (source.poll_interval_s / 60) * 1.5) return 'stale';
		return 'ok';
	}

	function getSourceDisplayConfig(source: (typeof data.sources)[0]): string {
		const config = source.source_config as Record<string, unknown>;
		if (source.source_type === 'telegram') return `${config.channel}`;
		if (source.source_type === 'rss') return String(config.url || config.feed_url || 'Нет URL');
		if (source.source_type === 'website') return String(config.url || 'Нет URL');
		return 'Неизвестно';
	}
</script>

<div class="container mx-auto max-w-3xl px-4 py-4">
	<Heading>Источники и статус сбора</Heading>

	{#if pageError}
		<div class="mb-4 rounded-lg border border-destructive bg-destructive/10 p-6 text-center">
			<p class="mb-4 text-destructive">
				{pageError.message || 'Произошла ошибка при загрузке данных'}
			</p>
			<Button variant="outline" onclick={() => window.location.reload()}>Повторить</Button>
		</div>
	{:else}
		<div class="mb-4 rounded-lg border bg-card p-3">
			<Collapsible bind:open={statusOpen}>
				<CollapsibleTrigger class="flex w-full items-center gap-2">
					<span
						class={getHealthColor(healthStatus)}
						class:w-3={true}
						class:h-3={true}
						class:rounded-full={true}
					></span>
					<span class="font-medium"
						>Статус системы: {healthStatus ? tHealthStatus(healthStatus) : 'Неизвестно'}</span
					>
					<ChevronDown
						class="ml-auto h-4 w-4 transition-transform {statusOpen ? 'rotate-180' : ''}"
					/>
				</CollapsibleTrigger>

				<CollapsibleContent class="mt-3 space-y-3">
					<div class="flex flex-wrap gap-x-4 gap-y-2 text-sm">
						<div class="flex items-center gap-2 text-muted-foreground">
							<Database class="h-4 w-4" />
							<span>PostgreSQL:</span>
							<span class={health?.postgres === 'healthy' ? 'text-green-500' : 'text-red-500'}
								>{health?.postgres ? tDbStatus(health.postgres) : '?'}</span
							>
						</div>
						<div class="flex items-center gap-2 text-muted-foreground">
							<Server class="h-4 w-4" />
							<span>ClickHouse:</span>
							<span class={health?.clickhouse === 'healthy' ? 'text-green-500' : 'text-red-500'}
								>{health?.clickhouse ? tDbStatus(health.clickhouse) : '?'}</span
							>
						</div>
					</div>

					{#if collector}
						<div class="flex gap-2">
							<div class="flex items-center gap-1 text-muted-foreground">
								<BrainCircuit class="h-4 w-4" /> ML:
							</div>
							<div
								class="flex flex-wrap gap-x-4 gap-y-1 rounded-sm border p-1 text-sm text-muted-foreground"
							>
								{health?.ml ? tDbStatus(health.ml) : '?'}
								<span>Очередь: {health?.ml_queue_size ?? '?'}</span>
								<div class="flex items-center gap-1">
									<span
										class={getProcessingStatusColor(processingStatus)}
										class:w-2={true}
										class:h-2={true}
										class:rounded-full={true}
									></span>
									<span>{getProcessingStatusText(processingStatus)}</span>
								</div>
								<span
									>Обработано: {collector.raw_posts_processed} из {collector.raw_posts_total}</span
								>
								{#if collector.raw_posts_pending > 0}
									<span class="text-blue-500">В очереди: {collector.raw_posts_pending}</span>
								{/if}
								{#if collector.raw_posts_failed > 0}
									<span class="text-destructive">Ошибок: {collector.raw_posts_failed}</span>
								{/if}
							</div>
						</div>
					{/if}
				</CollapsibleContent>
			</Collapsible>

			{#if health?.ml_error}
				<div class="mt-2 text-sm text-destructive">
					ML ошибка: {health.ml_error}
				</div>
			{/if}
		</div>

		<section>
			{#if data.sources}
				<div class="space-y-3">
					{#each data.sources as source (source.id)}
						{@const status = getSourceStatus(source)}
						<div class="rounded-lg border p-4">
							<div class="flex items-start gap-3 sm:gap-4">
								<div
									class="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted"
								>
									{#if source.source_type === 'telegram'}
										<Send class="h-5 w-5" />
									{:else if source.source_type === 'rss'}
										<Radio class="h-5 w-5" />
									{:else if source.source_type === 'website'}
										<Globe class="h-5 w-5" />
									{/if}
								</div>

								<div class="flex min-w-0 flex-1 flex-col">
									<div class="flex items-start justify-between gap-2">
										<div class="text-foreground flex flex-col gap-0.5 truncate">
											<div class="font-medium">{tSourceType(source.source_type as SourceType)}</div>
											<div
												class="text-sm text-muted-foreground"
												title={getSourceDisplayConfig(source)}
											>
												{getSourceDisplayConfig(source)}
											</div>
										</div>

										<div class="flex flex-col gap-2 items-end">
											<form
												method="POST"
												action="?/toggleSource"
												id="toggle-form-{source.id}"
												class="hidden shrink-0 items-center gap-2 sm:flex"
												use:enhance={() => {
													submittingSourceId = source.id;
													return async ({ result, update }) => {
														if (result.type === 'failure') {
															toast.error('Ошибка при обновлении источника');
														}
														await update();
														submittingSourceId = null;
													};
												}}
											>
												<input type="hidden" name="source_id" value={source.id} />
												<input type="hidden" name="project_id" value={project?.id} />
												<input
													type="hidden"
													name="current_state"
													value={String(source.is_active)}
												/>

												{#if submittingSourceId === source.id}
													<Spinner class="size-4" />
												{/if}

												<span class="text-sm {getStatusColor(status)}">
													• {getStatusText(status)}
												</span>

												<Switch
													checked={source.is_active}
													disabled={submittingSourceId === source.id}
													onCheckedChange={() => {
														const form = document.getElementById(
															'toggle-form-' + source.id
														) as HTMLFormElement | null;
														form?.requestSubmit();
													}}
												/>
											</form>

											<form
												method="POST"
												action="?/deleteSource"
												id="delete-form-{source.id}"
												class="hidden shrink-0 sm:block"
												use:enhance={() => {
													return async ({ result, update }) => {
														if (result.type === 'failure') {
															toast.error('Ошибка при удалении источника');
														} else if (result.type === 'success') {
															toast.success('Источник удалён');
														}
														await update();
													};
												}}
											>
												<input type="hidden" name="source_id" value={source.id} />
												<input type="hidden" name="project_id" value={project?.id} />
												<Button
													type="button"
													variant="ghost"
													size="icon"
													class="text-muted-foreground hover:text-destructive"
													onclick={() => {
														if (confirm(`Удалить источник "${getSourceDisplayConfig(source)}"?`)) {
															const form = document.getElementById(
																`delete-form-${source.id}`
															) as HTMLFormElement | null;
															form?.requestSubmit();
														}
													}}
												>
													<Trash2 class="h-4 w-4" />
												</Button>
											</form>
										</div>

										<span class="text-sm sm:hidden {getStatusColor(status)} truncate">
											• {getStatusText(status)}
										</span>
									</div>

									<div class="hidden flex-col gap-1 text-sm text-muted-foreground sm:flex">
										<div class="flex flex-wrap items-center gap-x-2 gap-y-1">
											<span class="whitespace-nowrap">
												{#if source.last_collected_at}
													Последний сбор: {new Date(source.last_collected_at).toLocaleString(
														'ru-RU'
													)}
												{:else}
													Ещё не собирался
												{/if}
											</span>
										</div>

										{#if source.last_error}
											<span
												class="break-words text-destructive"
												title={tSourceError(source.last_error)}
											>
												• {tSourceError(source.last_error)}
											</span>
										{/if}
									</div>
								</div>
							</div>

							<div class="mt-3 flex flex-col gap-2 sm:hidden">
								<div class="text-sm text-muted-foreground">
									{#if source.last_collected_at}
										Последний сбор: {new Date(source.last_collected_at).toLocaleString('ru-RU')}
									{:else}
										Ещё не собирался
									{/if}
								</div>

								{#if source.last_error}
									<div
										class="text-sm break-words text-destructive"
										title={tSourceError(source.last_error)}
									>
										• {tSourceError(source.last_error)}
									</div>
								{/if}

								<form
									method="POST"
									action="?/toggleSource"
									class="mt-1 w-full"
									use:enhance={() => {
										submittingSourceId = source.id;
										return async ({ result, update }) => {
											if (result.type === 'failure') {
												toast.error('Ошибка при обновлении источника');
											}
											await update();
											submittingSourceId = null;
										};
									}}
								>
									<input type="hidden" name="source_id" value={source.id} />
									<input type="hidden" name="project_id" value={project?.id} />
									<input type="hidden" name="current_state" value={String(source.is_active)} />

									<Button
										type="submit"
										variant={source.is_active ? 'secondary' : 'default'}
										class="w-full"
										disabled={submittingSourceId === source.id}
									>
										{#if submittingSourceId === source.id}
											<Spinner class="mr-2 size-4" />
										{/if}
										{source.is_active ? 'Отключить источник' : 'Включить источник'}
									</Button>
								</form>
							</div>
						</div>
					{:else}
						<div
							class="flex h-32 items-center justify-center rounded-lg border border-dashed border-border text-muted-foreground"
						>
							Нет источников
						</div>
					{/each}
				</div>
			{/if}

			<div class="mt-4 flex justify-end">
				<Button onclick={() => (addModalOpen = true)}>
					<Plus />
					Добавить источник
				</Button>
			</div>
		</section>
	{/if}

	<Dialog.Root bind:open={addModalOpen}>
		<Dialog.Content>
			<Dialog.Header>
				<Dialog.Title>Добавить источник</Dialog.Title>
				<Dialog.Description>Выберите тип источника и заполните необходимые поля</Dialog.Description>
			</Dialog.Header>

			<form
				method="POST"
				action="?/createSource"
				use:enhance={() => {
					isSubmittingNew = true;
					return async ({ result, update }) => {
						if (result.type === 'failure') {
							toast.error('Ошибка при создании источника');
						} else if (result.type === 'success') {
							toast.success('Источник добавлен');
							addModalOpen = false;
							sourceConfig = '';
							sourceType = 'telegram';
							pollInterval = 3600;
						}
						await update();
						isSubmittingNew = false;
					};
				}}
			>
				<input type="hidden" name="project_id" value={project?.id} />

				<div class="space-y-4 py-4">
					<div class="space-y-2">
						<label for="source_type" class="text-sm font-medium">Тип источника</label>
						<select
							id="source_type"
							name="source_type"
							bind:value={sourceType}
							class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
						>
							<option value="telegram">Telegram</option>
							<option value="rss">RSS</option>
							<option value="website">Website</option>
						</select>
					</div>

					<div class="space-y-2">
						<label for="source_config" class="text-sm font-medium">
							{#if sourceType === 'telegram'}Имя канала (без @){/if}
							{#if sourceType === 'rss'}URL ленты{/if}
							{#if sourceType === 'website'}URL сайта{/if}
						</label>
						<input
							id="source_config"
							name="source_config"
							type="text"
							bind:value={sourceConfig}
							placeholder={sourceType === 'telegram' ? 'durov' : 'https://example.com/rss.xml'}
							class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
							required
						/>
					</div>

					<div class="space-y-2">
						<label for="poll_interval" class="text-sm font-medium">Интервал опроса (секунды)</label>
						<input
							id="poll_interval"
							name="poll_interval"
							type="number"
							bind:value={pollInterval}
							min="60"
							class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
						/>
					</div>
				</div>

				<Dialog.Footer>
					<Button type="button" variant="outline" onclick={() => (addModalOpen = false)}
						>Отмена</Button
					>
					<Button type="submit" disabled={isSubmittingNew || !sourceConfig.trim()}>
						{#if isSubmittingNew}
							<Spinner class="mr-2 h-4 w-4" />
						{/if}
						Добавить
					</Button>
				</Dialog.Footer>
			</form>
		</Dialog.Content>
	</Dialog.Root>
</div>
