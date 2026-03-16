import { writable } from 'svelte/store';

export const confidence = writable<string>('0.7');
export const period = writable<string>('7d');
