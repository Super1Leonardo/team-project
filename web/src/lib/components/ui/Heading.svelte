<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { HTMLAttributes } from 'svelte/elements';
	import { type WithElementRef } from '$lib/utils';

	let {
		children,
		class: className,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLHeadingElement>> & {
		children: Snippet;
		className?: string;
	} = $props();
</script>

<h1 class={'mt-8 text-3xl font-semibold ' + className} {...restProps}>
	{@render children()}
</h1>
