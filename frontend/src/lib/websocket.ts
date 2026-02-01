// WebSocket connection manager with Svelte stores

import { writable, derived, type Writable } from 'svelte/store';
import type { GameEvent, WSMessage, SeriesStatus, GamePhase, SnapshotPlayer } from './types';

const WS_URL = 'ws://localhost:8000/ws';

export interface ConnectionState {
	connected: boolean;
	subscribedTo: string | null;
	error: string | null;
}

export interface GameSnapshot {
	game_id: string;
	alive_player_ids: string[];
	phase: GamePhase;
	day_number: number;
	players: SnapshotPlayer[];
}

export interface SeriesProgress {
	series_id: string;
	status: SeriesStatus;
	game_number: number;
	total_games: number;
}

// Stores
export const connectionState: Writable<ConnectionState> = writable({
	connected: false,
	subscribedTo: null,
	error: null
});

export const events: Writable<GameEvent[]> = writable([]);
export const snapshot: Writable<GameSnapshot | null> = writable(null);
export const seriesProgress: Writable<SeriesProgress | null> = writable(null);
export const audioEnabled: Writable<boolean> = writable(false);

// Human player state
export interface HumanTurnState {
	isMyTurn: boolean;
	action: 'speech' | 'vote' | 'night_action' | null;
	validTargets: string[];
	role: string | null;
}

// Human player stores
export const humanPlayerId: Writable<string | null> = writable(null);
export const humanTurnState: Writable<HumanTurnState> = writable({
	isMyTurn: false,
	action: null,
	validTargets: [],
	role: null
});

// Derived stores for round table UI
export const currentSpeaker = derived(events, ($events) => {
	const lastSpeech = [...$events].reverse().find((e) => e.type === 'speech');
	if (!lastSpeech) return null;
	const payload = lastSpeech.payload as { content?: string; player_name?: string };
	return {
		playerId: lastSpeech.actor_id,
		playerName: payload.player_name || 'Unknown',
		content: payload.content || ''
	};
});

export const currentVotes = derived(events, ($events) => {
	const votes = new Map<string, string>();
	let lastPhaseChangeIndex = -1;

	$events.forEach((e, i) => {
		if (e.type === 'phase_changed' || e.type === 'day_started' || e.type === 'night_started') {
			lastPhaseChangeIndex = i;
			votes.clear();
		}
		if (e.type === 'vote_cast' && i > lastPhaseChangeIndex) {
			// Use actor_id (voter) and target_id from the event level
			if (e.actor_id && e.target_id) {
				votes.set(e.actor_id, e.target_id);
			}
		}
	});

	return votes;
});

let ws: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let currentSeriesId: string | null = null;
let pendingAudioEnabled: boolean = false; // Track audio state to send after subscription

export function connect(seriesId: string): void {
	// Clean up existing connection
	disconnect();
	currentSeriesId = seriesId;

	try {
		ws = new WebSocket(WS_URL);

		ws.onopen = () => {
			console.log('WebSocket connected');
			connectionState.set({
				connected: true,
				subscribedTo: null,
				error: null
			});

			// Subscribe to series
			ws?.send(
				JSON.stringify({
					type: 'subscribe',
					payload: {
						series_id: seriesId,
						viewer_mode: true
					}
				})
			);
		};

		ws.onmessage = (event) => {
			try {
				const message: WSMessage = JSON.parse(event.data);
				handleMessage(message);
			} catch (e) {
				console.error('Failed to parse WebSocket message:', e);
			}
		};

		ws.onclose = () => {
			console.log('WebSocket disconnected');
			connectionState.update((s) => ({ ...s, connected: false }));

			// Attempt to reconnect after 3 seconds
			if (currentSeriesId) {
				reconnectTimeout = setTimeout(() => {
					if (currentSeriesId) {
						connect(currentSeriesId);
					}
				}, 3000);
			}
		};

		ws.onerror = (error) => {
			console.error('WebSocket error:', error);
			connectionState.update((s) => ({
				...s,
				error: 'Connection error'
			}));
		};
	} catch (e) {
		console.error('Failed to create WebSocket:', e);
		connectionState.update((s) => ({
			...s,
			error: 'Failed to connect'
		}));
	}
}

export function disconnect(): void {
	currentSeriesId = null;

	if (reconnectTimeout) {
		clearTimeout(reconnectTimeout);
		reconnectTimeout = null;
	}

	if (ws) {
		ws.close();
		ws = null;
	}

	// Reset stores
	connectionState.set({
		connected: false,
		subscribedTo: null,
		error: null
	});
	events.set([]);
	snapshot.set(null);
	seriesProgress.set(null);
}

function handleMessage(message: WSMessage): void {
	switch (message.type) {
		case 'subscribed':
			connectionState.update((s) => ({
				...s,
				subscribedTo: message.payload.series_id
			}));
			// Send audio preference immediately after subscription
			if (pendingAudioEnabled && ws && ws.readyState === WebSocket.OPEN) {
				console.log('Sending audio preference after subscription:', pendingAudioEnabled);
				ws.send(
					JSON.stringify({
						type: 'set_audio',
						payload: { enabled: pendingAudioEnabled }
					})
				);
			}
			break;

		case 'event':
			events.update((e) => [...e, message.payload]);
			break;

		case 'snapshot':
			snapshot.set(message.payload);
			break;

		case 'series_status':
			seriesProgress.set(message.payload);
			break;

		case 'error':
			console.error('Server error:', message.payload);
			connectionState.update((s) => ({
				...s,
				error: message.payload.message
			}));
			break;

		case 'audio_updated':
			audioEnabled.set(message.payload.enabled);
			break;

		// Human voice messages
		case 'human_turn_start':
			humanTurnState.set({
				isMyTurn: true,
				action: message.payload.action,
				validTargets: [],
				role: null
			});
			break;

		case 'human_turn_end':
			humanTurnState.set({
				isMyTurn: false,
				action: null,
				validTargets: [],
				role: null
			});
			break;

		case 'human_vote_required':
			humanTurnState.set({
				isMyTurn: true,
				action: 'vote',
				validTargets: message.payload.valid_targets,
				role: null
			});
			break;

		case 'human_night_action_required':
			humanTurnState.set({
				isMyTurn: true,
				action: 'night_action',
				validTargets: message.payload.valid_targets,
				role: message.payload.role
			});
			break;

		default:
			console.warn('Unknown message type:', message);
	}
}

export function clearEvents(): void {
	events.set([]);
}

export function setAudioEnabled(enabled: boolean): void {
	audioEnabled.set(enabled);
	pendingAudioEnabled = enabled; // Track for sending after (re)connection
	if (ws && ws.readyState === WebSocket.OPEN) {
		console.log('Sending audio preference:', enabled);
		ws.send(
			JSON.stringify({
				type: 'set_audio',
				payload: { enabled }
			})
		);
	}
}

// Human player input functions

export function sendHumanSpeech(seriesId: string, text: string): void {
	if (!ws || ws.readyState !== WebSocket.OPEN) return;

	ws.send(
		JSON.stringify({
			type: 'human_speech',
			payload: {
				series_id: seriesId,
				text
			}
		})
	);

	// Clear turn state
	humanTurnState.set({
		isMyTurn: false,
		action: null,
		validTargets: [],
		role: null
	});
}

export function sendHumanVote(seriesId: string, target: string): void {
	if (!ws || ws.readyState !== WebSocket.OPEN) return;

	ws.send(
		JSON.stringify({
			type: 'human_vote',
			payload: {
				series_id: seriesId,
				target
			}
		})
	);

	// Clear turn state
	humanTurnState.set({
		isMyTurn: false,
		action: null,
		validTargets: [],
		role: null
	});
}

export function sendHumanNightAction(seriesId: string, target: string): void {
	if (!ws || ws.readyState !== WebSocket.OPEN) return;

	ws.send(
		JSON.stringify({
			type: 'human_night_action',
			payload: {
				series_id: seriesId,
				target
			}
		})
	);

	// Clear turn state
	humanTurnState.set({
		isMyTurn: false,
		action: null,
		validTargets: [],
		role: null
	});
}

export function setHumanPlayerId(playerId: string | null): void {
	humanPlayerId.set(playerId);
}
