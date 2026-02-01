/**
 * Voice client for human player communication using Daily.co WebRTC.
 *
 * Handles:
 * - Connecting to Daily room for voice chat
 * - Capturing and streaming microphone audio
 * - Receiving AI player audio
 * - Managing mute/unmute state
 */

import { writable, type Writable } from 'svelte/store';

export type VoiceConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface VoiceState {
	connectionState: VoiceConnectionState;
	isMuted: boolean;
	isListening: boolean;
	isSpeaking: boolean;
	error: string | null;
}

// Stores for voice state
export const voiceState: Writable<VoiceState> = writable({
	connectionState: 'disconnected',
	isMuted: false,
	isListening: false,
	isSpeaking: false,
	error: null
});

// Daily call object (lazy loaded)
let dailyCall: any = null;
let Daily: any = null;

/**
 * Initialize the Daily SDK (lazy load to avoid SSR issues)
 */
async function initDaily(): Promise<void> {
	if (Daily) return;

	try {
		const module = await import('@daily-co/daily-js');
		Daily = module.default;
	} catch (e) {
		console.error('Failed to load Daily SDK:', e);
		throw new Error('Voice chat not available');
	}
}

/**
 * Connect to a Daily room for voice chat.
 */
export async function connectVoice(roomUrl: string, token: string): Promise<void> {
	await initDaily();

	voiceState.update((s) => ({ ...s, connectionState: 'connecting', error: null }));

	try {
		dailyCall = Daily.createCallObject({
			audioSource: true,
			videoSource: false
		});

		// Set up event handlers
		dailyCall.on('joined-meeting', () => {
			voiceState.update((s) => ({ ...s, connectionState: 'connected' }));
		});

		dailyCall.on('left-meeting', () => {
			voiceState.update((s) => ({ ...s, connectionState: 'disconnected' }));
		});

		dailyCall.on('error', (e: any) => {
			console.error('Daily error:', e);
			voiceState.update((s) => ({
				...s,
				connectionState: 'error',
				error: e.errorMsg || 'Connection error'
			}));
		});

		// Join the room
		await dailyCall.join({
			url: roomUrl,
			token: token
		});
	} catch (e) {
		console.error('Failed to connect voice:', e);
		voiceState.update((s) => ({
			...s,
			connectionState: 'error',
			error: e instanceof Error ? e.message : 'Failed to connect'
		}));
	}
}

/**
 * Disconnect from the voice chat.
 */
export async function disconnectVoice(): Promise<void> {
	if (dailyCall) {
		try {
			await dailyCall.leave();
			await dailyCall.destroy();
		} catch (e) {
			console.error('Error leaving call:', e);
		}
		dailyCall = null;
	}

	voiceState.update((s) => ({
		...s,
		connectionState: 'disconnected',
		isMuted: false,
		isListening: false,
		isSpeaking: false,
		error: null
	}));
}

/**
 * Toggle mute state.
 */
export function toggleMute(): void {
	if (!dailyCall) return;

	voiceState.update((s) => {
		const newMuted = !s.isMuted;
		dailyCall.setLocalAudio(!newMuted);
		return { ...s, isMuted: newMuted };
	});
}

/**
 * Set mute state explicitly.
 */
export function setMuted(muted: boolean): void {
	if (!dailyCall) return;

	dailyCall.setLocalAudio(!muted);
	voiceState.update((s) => ({ ...s, isMuted: muted }));
}

/**
 * Check if voice is currently connected.
 */
export function isVoiceConnected(): boolean {
	let connected = false;
	voiceState.subscribe((s) => {
		connected = s.connectionState === 'connected';
	})();
	return connected;
}
