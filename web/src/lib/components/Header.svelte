<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { cn } from '$lib/utils';
	import { confidence, period } from '$lib/stores/filters';
	import * as NavigationMenu from './ui/shadcn/navigation-menu';
	import { navigationMenuTriggerStyle } from './ui/shadcn/navigation-menu/navigation-menu-trigger.svelte';

	let {
		health = null
	}: {
		health?: { status: string; postgres: string; clickhouse: string; ml_queue_size: number } | null;
	} = $props();

	const links = $derived([
		{
			title: 'Новости',
			url: buildUrl('/')
		},
		{
			title: 'Аналитика',
			url: buildUrl('/analytics')
		},
		{
			title: 'Источники',
			url: buildUrl('/sources'),
			showErrorDot: true
		},
		{
			title: 'Настройки',
			url: buildUrl('/setup')
		}
	]);

	function buildUrl(path: string): string {
		const params = new URLSearchParams();
		if ($confidence) params.set('confidence', $confidence);
		if ($period) params.set('period', $period);
		const query = params.toString();
		const base = resolve(path as '/') as string;
		return base + (query ? `?${query}` : '');
	}

	const currentUrl = $derived(page.url.pathname);

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
</script>

<NavigationMenu.Root class="mx-auto">
	<NavigationMenu.List class="md:gap-4">
		{#each links as { title, url, showErrorDot } (url)}
			<NavigationMenu.Item>
				<NavigationMenu.Link>
					{#snippet child()}
						<a
							href={url}
							class={cn(
								navigationMenuTriggerStyle(),
								'relative transition-all',
								currentUrl === url &&
									'bg-primary text-primary-foreground hover:bg-primary-foreground hover:text-primary'
							)}
						>
							{title}
							{#if showErrorDot && health?.status && health.status !== 'healthy'}
								<span
									class={cn(
										'absolute -top-1 -right-1 h-3 w-3 rounded-full',
										getHealthColor(health.status)
									)}
								></span>
							{/if}
						</a>
					{/snippet}
				</NavigationMenu.Link>
			</NavigationMenu.Item>
		{/each}
	</NavigationMenu.List>
</NavigationMenu.Root>
