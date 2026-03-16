import { writable, get } from 'svelte/store';

let intervalId: ReturnType<typeof setInterval> | null = null;

export const countdown = writable(0);
export const countdownActive = writable(false);

function getIntervalMinutes(): number {
	if (typeof window === 'undefined') return 5;
	const stored = localStorage.getItem('feedRefreshInterval');
	if (!stored) return 5;
	const parsed = parseInt(stored, 10);
	return isNaN(parsed) || parsed < 1 || parsed > 60 ? 5 : parsed;
}

export function startCountdown(onRefresh: () => void): void {
	stopCountdown();
	
	const intervalMinutes = getIntervalMinutes();
	const totalSeconds = intervalMinutes * 60;
	
	countdown.set(totalSeconds);
	countdownActive.set(true);
	
	intervalId = setInterval(() => {
		const current = get(countdown);
		if (current <= 1) {
			onRefresh();
			countdown.set(totalSeconds);
		} else {
			countdown.set(current - 1);
		}
	}, 1000);
}

export function stopCountdown(): void {
	if (intervalId) {
		clearInterval(intervalId);
		intervalId = null;
	}
	countdownActive.set(false);
}

export function formatCountdown(seconds: number): string {
	const mins = Math.floor(seconds / 60);
	const secs = seconds % 60;
	return `${mins}:${secs.toString().padStart(2, '0')}`;
}
