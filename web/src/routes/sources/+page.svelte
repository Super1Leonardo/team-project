<script lang="ts">
	import { enhance } from '$app/forms';
	import { toast } from 'svelte-sonner';
	import Heading from '$lib/components/ui/Heading.svelte';
	import { Switch } from '$lib/components/ui/shadcn/switch';
	import Spinner from '$lib/components/ui/shadcn/spinner/spinner.svelte';
	import { Send, MessageCircle, Radio, Server, Database, BrainCircuit } from '@lucide/svelte';
	import {
		tSourceType,
		tSourceStatus,
		tSourceError,
		tHealthStatus,
		tDbStatus,
		type SourceType
	} from '$lib/utils';

	let { data } = $props();

	let isSubmitting = $state(false);

	const project = $derived(data.project);
	const health = $derived(data.health);
	const healthStatus = $derived(health?.status ?? null);

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
		if (source.source_type === 'telegram') {
			return `@${config.channel}`;
		}
		if (source.source_type === 'vk') {
			return String(config.domain || `ID: ${config.group_id}`);
		}
		if (source.source_type === 'rss') {
			return String(config.url || config.feed_url || 'Нет URL');
		}
		return 'Неизвестно';
	}
</script>

<div class="container mx-auto max-w-3xl py-4">
	<Heading>Источники и статус сбора</Heading>

	<div class="mb-4 p-3 rounded-lg border bg-card">
		<div class="flex items-center gap-2 mb-2">
			<span
				class={getHealthColor(healthStatus)}
				class:w-3={true}
				class:h-3={true}
				class:rounded-full={true}
			></span>
			<span class="font-medium"
				>Статус системы: {healthStatus ? tHealthStatus(healthStatus) : 'Неизвестно'}</span
			>
		</div>
		<div class="flex gap-4 text-sm text-muted-foreground">
			<div class="flex items-center gap-1">
				<Database class="w-4 h-4" />
				<span>PostgreSQL: {health?.postgres ? tDbStatus(health.postgres) : '?'}</span>
			</div>
			<div class="flex items-center gap-1">
				<Server class="w-4 h-4" />
				<span>ClickHouse: {health?.clickhouse ? tDbStatus(health.clickhouse) : '?'}</span>
			</div>
			<div class="flex items-center gap-1">
				<BrainCircuit class="w-4 h-4" />
				<span>ML очередь: {health?.ml_queue_size ?? '?'}</span>
			</div>
		</div>
	</div>

	<section>
		{#if data.sources}
			<div class="space-y-3">
				{#each data.sources as source (source.id)}
					{@const status = getSourceStatus(source)}
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
									<span class="font-medium">{tSourceType(source.source_type as SourceType)}</span>
									<span class="text-muted-foreground">{getSourceDisplayConfig(source)}</span>
									<span class={getStatusColor(status)}>• {getStatusText(status)}</span>
								</div>
								<div class="flex items-center gap-2 text-sm text-muted-foreground">
									{#if source.last_collected_at}
										Последний сбор: {new Date(source.last_collected_at).toLocaleString('ru-RU')}
									{:else}
										Ещё не собирался
									{/if}
									{#if source.last_error}
										<span class="text-destructive">• {tSourceError(source.last_error)}</span>
									{/if}
								</div>
							</div>
						</div>

						<form
							method="POST"
							action="?/toggleSource"
							id="toggle-form-{source.id}"
							use:enhance={() => {
								isSubmitting = true;
								return async ({ result, update }) => {
									if (result.type === 'failure') {
										toast.error('Ошибка при обновлении источника');
									}
									await update();
									isSubmitting = false;
								};
							}}
						>
							<input type="hidden" name="source_id" value={source.id} />
							<input type="hidden" name="project_id" value={project?.id} />
							<input type="hidden" name="current_state" value={String(source.is_active)} />
							<div class="flex items-center gap-2">
								{#if isSubmitting}
									<Spinner class="size-4" />
								{/if}
								<Switch
									checked={source.is_active}
									disabled={isSubmitting}
									onCheckedChange={() => {
										const form = document.getElementById(
											'toggle-form-' + source.id
										) as HTMLFormElement | null;
										form?.requestSubmit();
									}}
								/>
							</div>
						</form>
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
	</section>
</div>
