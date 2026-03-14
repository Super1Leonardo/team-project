<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { cn } from '$lib/utils';
	import * as NavigationMenu from './ui/shadcn/navigation-menu';
	import { navigationMenuTriggerStyle } from './ui/shadcn/navigation-menu/navigation-menu-trigger.svelte';

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
			title: 'Состояние',
			url: resolve('/health')
		},
		{
			title: 'Настройки',
			url: resolve('/setup')
		}
	];

	const currentUrl = $derived(page.url.pathname);
</script>

<NavigationMenu.Root>
	<NavigationMenu.List class="gap-4">
		{#each links as { title, url } (url)}
			<NavigationMenu.Item>
				<NavigationMenu.Link>
					{#snippet child()}
						<a
							href={url}
							class={cn(
								navigationMenuTriggerStyle(),
								'transition-all',
								currentUrl === url &&
									'bg-primary text-primary-foreground hover:bg-primary-foreground hover:text-primary'
							)}
						>
							{title}
						</a>
					{/snippet}
				</NavigationMenu.Link>
			</NavigationMenu.Item>
		{/each}
	</NavigationMenu.List>
</NavigationMenu.Root>
