<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import Header from '$lib/components/Header.svelte';

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="pt-4 px-8">
	<Header />
	<div class="max-w-prose mx-auto">
		{@render children()}
	</div>
</div>
