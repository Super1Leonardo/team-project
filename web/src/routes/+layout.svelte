<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import Header from '$lib/components/Header.svelte';
	import { Toaster } from 'svelte-sonner';
	import * as Tooltip from '$lib/components/ui/shadcn/tooltip';

	let { children, data } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<Toaster richColors={true} position="top-right" />

<Tooltip.Provider>
	<div class="pt-4 px-8">
		<Header health={data.health} />
		<div class="max-w-prose mx-auto">
			{@render children()}
		</div>
	</div>
</Tooltip.Provider>
