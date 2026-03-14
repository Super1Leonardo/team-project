<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="max-w-prose mx-auto">
	<div class="px-2">
		{@render children()}
	</div>
</div>
