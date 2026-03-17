<script lang="ts">
	import * as Dialog from '$lib/components/ui/shadcn/dialog';
	import { Button } from '$lib/components/ui/shadcn/button';
	import * as Checkbox from '$lib/components/ui/shadcn/checkbox';
	import { 
		shouldShowPermissionDialog, 
		notificationPermission,
		requestNotificationPermission,
		setNotificationsEnabled,
		setDontAskAgain,
		initNotifications
	} from '$lib/stores/notifications';
	import { onMount } from 'svelte';

	let open = $state(false);
	let dontAskChecked = $state(false);

	onMount(() => {
		initNotifications();
	});

	$effect(() => {
		open = $shouldShowPermissionDialog;
	});

	async function handleEnable() {
		const granted = await requestNotificationPermission();
		if (granted) {
			setNotificationsEnabled(true);
		}
		if (dontAskChecked) {
			setDontAskAgain(true);
		}
		open = false;
	}

	function handleDecline() {
		if (dontAskChecked) {
			setDontAskAgain(true);
		}
		open = false;
	}
</script>

<Dialog.Root bind:open={open} onOpenChange={(isOpen) => {
	if (!isOpen) {
		open = false;
	}
}}>
	<Dialog.Content class="max-w-md">
		<Dialog.Header>
			<Dialog.Title>Включить уведомления?</Dialog.Title>
			<Dialog.Description>
				Получайте мгновенные уведомления о новых рисковых статьях прямо в браузере.
			</Dialog.Description>
		</Dialog.Header>

		<div class="flex items-center gap-2 py-2">
			<Checkbox.Root 
				bind:checked={dontAskChecked}
				id="dont-ask-again"
			/>
			<label 
				for="dont-ask-again" 
				class="text-sm text-muted-foreground cursor-pointer"
			>
				Больше не спрашивать
			</label>
		</div>

		<Dialog.Footer>
			<Button variant="outline" onclick={handleDecline}>
				Нет, спасибо
			</Button>
			<Button onclick={handleEnable}>
				Включить
			</Button>
		</Dialog.Footer>
	</Dialog.Content>
</Dialog.Root>
