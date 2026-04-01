import { writable, get, derived } from 'svelte/store';

const NOTIFIED_IDS_KEY = 'notifiedCriticalIds';
const NOTIFICATIONS_ENABLED_KEY = 'notificationsEnabled';
const DONT_ASK_AGAIN_KEY = 'notificationDialogDontAsk';

function loadNotifiedIds(): Set<number> {
	if (typeof window === 'undefined') return new Set();
	const stored = localStorage.getItem(NOTIFIED_IDS_KEY);
	if (!stored) return new Set();
	try {
		const parsed = JSON.parse(stored);
		return new Set(Array.isArray(parsed) ? parsed : []);
	} catch {
		return new Set();
	}
}

function saveNotifiedIds(ids: Set<number>) {
	if (typeof window === 'undefined') return;
	localStorage.setItem(NOTIFIED_IDS_KEY, JSON.stringify([...ids]));
}

function loadNotificationsEnabled(): boolean {
	if (typeof window === 'undefined') return false;
	const stored = localStorage.getItem(NOTIFICATIONS_ENABLED_KEY);
	return stored === 'true';
}

function saveNotificationsEnabled(enabled: boolean) {
	if (typeof window === 'undefined') return;
	localStorage.setItem(NOTIFICATIONS_ENABLED_KEY, String(enabled));
}

function loadDontAskAgain(): boolean {
	if (typeof window === 'undefined') return false;
	const stored = localStorage.getItem(DONT_ASK_AGAIN_KEY);
	return stored === 'true';
}

function saveDontAskAgain(dontAsk: boolean) {
	if (typeof window === 'undefined') return;
	localStorage.setItem(DONT_ASK_AGAIN_KEY, String(dontAsk));
}

export const notificationsEnabled = writable<boolean>(false);
export const notifiedCriticalIds = writable<Set<number>>(new Set());
export const notificationPermission = writable<NotificationPermission>('default');
export const dontAskAgain = writable<boolean>(false);

export const shouldShowPermissionDialog = derived(
	[notificationPermission, dontAskAgain],
	([$permission, $dontAsk]) => $permission === 'default' && !$dontAsk
);

export function initNotifications() {
	if (typeof window === 'undefined') return;
	
	notificationPermission.set(Notification.permission);
	notificationsEnabled.set(loadNotificationsEnabled());
	notifiedCriticalIds.set(loadNotifiedIds());
	dontAskAgain.set(loadDontAskAgain());
}

export async function requestNotificationPermission(): Promise<boolean> {
	if (typeof window === 'undefined') return false;
	
	const permission = await Notification.requestPermission();
	notificationPermission.set(permission);
	return permission === 'granted';
}

export function setNotificationsEnabled(enabled: boolean) {
	notificationsEnabled.set(enabled);
	saveNotificationsEnabled(enabled);
}

export function clearDontAskAgain() {
	dontAskAgain.set(false);
	saveDontAskAgain(false);
}

export function setDontAskAgain(dontAsk: boolean) {
	dontAskAgain.set(dontAsk);
	saveDontAskAgain(dontAsk);
}

export function addNotifiedId(id: number) {
	const ids = get(notifiedCriticalIds);
	ids.add(id);
	notifiedCriticalIds.set(ids);
	saveNotifiedIds(ids);
}

export async function showCriticalArticleNotification(
	title: string,
	body: string,
	onClick?: () => void
): Promise<void> {
	if (typeof window === 'undefined') return;
	
	if (Notification.permission === 'granted') {
		const notification = new Notification(title, {
			body,
			icon: '/favicon.ico',
			badge: '/favicon.ico',
			tag: 'critical-article',
		});
		
		if (onClick) {
			notification.onclick = () => {
				window.focus();
				onClick();
				notification.close();
			};
		}
	}
}
