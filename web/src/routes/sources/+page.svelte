<script lang="ts">
	import { enhance } from '$app/forms';
	import Heading from '$lib/components/ui/Heading.svelte';
	import { Switch } from '$lib/components/ui/shadcn/switch';
	import { Send, MessageCircle, Radio } from '@lucide/svelte';
	import { tSourceType, tSourceStatus, tSourceError, type SourceType } from '$lib/utils';

	let { data } = $props();

	function getSourceDisplayConfig(source: (typeof data.sources)[0]): string {
		if (source.source_type === 'telegram') {
			return `@${source.source_config.channel}`;
		}
		if (source.source_type === 'vk') {
			return source.source_config.domain || `ID: ${source.source_config.group_id}`;
		}
		if (source.source_type === 'rss') {
			return source.source_config.feed_url || 'Нет URL';
		}
		return 'Неизвестно';
	}

	function getSourceStatus(source: (typeof data.sources)[0]): 'ok' | 'error' | 'stale' {
		if (source.last_error) return 'error';
		if (!source.last_collected_at) return 'stale';

		const lastCollected = new Date(source.last_collected_at);
		const now = new Date();
		const diffMinutes = (now.getTime() - lastCollected.getTime()) / (1000 * 60);

		if (diffMinutes > (source.poll_interval_s / 60) * 1.5) return 'stale';
		return 'ok';
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
</script>

<div class="container mx-auto max-w-3xl py-4">
	<Heading>Источники и статус сбора</Heading>

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
							use:enhance={() => {
								return async ({ update }) => {
									await update();
								};
							}}
						>
							<input type="hidden" name="source_id" value={source.id} />
							<Switch checked={source.is_active} />
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
