<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { cn } from '$lib/utils';
	import * as NavigationMenu from './ui/shadcn/navigation-menu';
	import { navigationMenuTriggerStyle } from './ui/shadcn/navigation-menu/navigation-menu-trigger.svelte';

	let { hasErrors = false }: { hasErrors?: boolean } = $props();

	const links = [
		{
			title: 'Новости',
			url: resolve('/')
		},
		{
			title: 'Аналитика',
			url: resolve('/analytics')
		},
		{
			title: 'Источники',
			url: resolve('/sources'),
			showErrorDot: true
		},
		{
			title: 'Настройки',
			url: resolve('/setup')
		}
	];

	const currentUrl = $derived(page.url.pathname);
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
							{#if showErrorDot && hasErrors}
								<span class="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-red-500"></span>
							{/if}
						</a>
					{/snippet}
				</NavigationMenu.Link>
			</NavigationMenu.Item>
		{/each}
	</NavigationMenu.List>
</NavigationMenu.Root>
