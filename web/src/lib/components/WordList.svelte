<script lang="ts">
	import { Badge } from '$lib/components/ui/shadcn/badge';
	import { Input } from '$lib/components/ui/shadcn/input';
	import { Button } from '$lib/components/ui/shadcn/button';
	import { X, Plus } from '@lucide/svelte';

	let {
		label,
		words = $bindable([]),
		description = '',
		id = `word-input-${Math.random().toString(36).slice(2, 9)}`
	}: {
		label: string;
		words?: string[];
		description?: string;
		id?: string;
	} = $props();

	let inputValue = $state('');
	let placeholder = $state('Введите слово...');

	function addWord() {
		const trimmed = inputValue.trim();
		if (trimmed && !words.includes(trimmed)) {
			words = [...words, trimmed];
			inputValue = '';
		}
	}

	function removeWord(word: string) {
		words = words.filter((w) => w !== word);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addWord();
		}
	}
</script>

<div class="space-y-2">
	<label
		for={id}
		class="block mb-2 text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
	>
		{label}
	</label>

	<div class="flex gap-2">
		<Input {id} bind:value={inputValue} {placeholder} onkeydown={handleKeydown} class="flex-1" />
		<Button
			type="button"
			variant={!inputValue.trim() ? 'outline' : 'default'}
			size="icon"
			onclick={addWord}
			disabled={!inputValue.trim()}
		>
			<Plus />
		</Button>
	</div>

	{#if words.length > 0}
		<div class="flex flex-wrap gap-2">
			{#each words as word (word)}
				<Badge variant="outline" class="gap-1 pr-1">
					{word}
					<button
						type="button"
						class="ml-1 rounded-full p-px hover:text-primary-foreground hover:bg-destructive focus:outline-none"
						onclick={() => removeWord(word)}
						aria-label="Удалить {word}"
					>
						<X class="h-3 w-3" strokeWidth={3} />
					</button>
				</Badge>
			{/each}
		</div>
	{/if}

	{#if description}
		<p class="text-sm text-muted-foreground">{description}</p>
	{/if}
</div>
