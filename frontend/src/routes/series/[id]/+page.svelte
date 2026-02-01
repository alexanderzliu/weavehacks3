<script lang="ts">
	import { onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { fetchSeriesById, fetchSeriesGames, stopSeries, startSeries, fetchSeriesPlayers, fetchPlayerCheatsheet, fetchGame, fetchGameEvents } from '$lib/api';
	import {
		connect,
		disconnect,
		connectionState,
		events,
		snapshot,
		seriesProgress
	} from '$lib/websocket';
	import type { SeriesResponse, Cheatsheet, GameResponse, GameEvent, GamePhase } from '$lib/types';
	import RoundTable from '$lib/components/RoundTable.svelte';
	import ChatLog from '$lib/components/ChatLog.svelte';
	import PhaseIndicator from '$lib/components/PhaseIndicator.svelte';
	import CheatsheetDiffModal from '$lib/components/CheatsheetDiffModal.svelte';

	let series = $state<SeriesResponse | null>(null);
	let games = $state<
		Array<{
			id: string;
			game_number: number;
			status: string;
			winner: string | null;
			day_number: number;
		}>
	>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Player data with UUIDs
	let seriesPlayers = $state<Array<{ id: string; name: string; model_provider: string; model_name: string }>>([]);

	// Cheatsheet cache and loading state
	let cheatsheets = $state<Map<string, Cheatsheet>>(new Map());
	let loadingCheatsheet = $state<string | null>(null);

	// Cheatsheet diff modal state
	let diffModalPlayer = $state<{ id: string; name: string } | null>(null);

	// History viewing state
	let viewingGameId = $state<string | null>(null);
	let historyGame = $state<GameResponse | null>(null);
	let historyEvents = $state<GameEvent[]>([]);
	let historyLoading = $state(false);

	// Replay state
	let isReplaying = $state(false);

	// Derived status from WebSocket (real-time) or series data (initial load)
	let currentSeriesStatus = $derived($seriesProgress?.status ?? series?.status ?? 'pending');
	let replayIndex = $state(0);
	let replayTimer = $state<ReturnType<typeof setTimeout> | null>(null);
	let waitingForSpeech = $state(false); // True when waiting for speech to finish streaming
	const NON_SPEECH_DELAY_MS = 400; // Delay for non-speech events
	const POST_SPEECH_DELAY_MS = 800; // Delay after speech finishes before next event

	// Live mode buffering state (mirrors replay behavior)
	let liveEventQueue = $state<GameEvent[]>([]);
	let displayedLiveEvents = $state<GameEvent[]>([]);
	let liveWaitingForSpeech = $state(false);
	let liveTimer = $state<ReturnType<typeof setTimeout> | null>(null);
	let lastProcessedEventCount = $state(0); // Track how many events we've seen from $events
	let liveInitialized = $state(false); // Track if we've done initial catch-up
	let speechBubbleKey = $state(0); // Key to force SpeechBubble re-render

	// Player name to ID lookup
	let playerIdByName = $derived.by(() => {
		const map = new Map<string, string>();
		for (const p of seriesPlayers) {
			map.set(p.name, p.id);
		}
		return map;
	});

	// Reconstruct game snapshot at a specific event index (for replay)
	function reconstructSnapshot(game: GameResponse | null, evts: GameEvent[], upToIndex: number) {
		if (!game) return null;

		// Start with all players alive
		const aliveSet = new Set(game.players.map((p) => p.name));
		let phase: GamePhase = 'day';
		let dayNumber = 1;

		for (let i = 0; i <= upToIndex && i < evts.length; i++) {
			const e = evts[i];
			const payload = e.payload as Record<string, unknown>;
			if (e.type === 'day_started') {
				phase = 'day';
				dayNumber = (payload.day_number as number) || dayNumber;
			} else if (e.type === 'night_started') {
				phase = 'night';
			} else if (e.type === 'lynch_result' && payload.lynched_player_name) {
				aliveSet.delete(payload.lynched_player_name as string);
			} else if (e.type === 'night_result' && payload.killed_player_name) {
				aliveSet.delete(payload.killed_player_name as string);
			} else if (e.type === 'game_ended') {
				phase = 'completed';
			}
		}

		return {
			game_id: game.id,
			alive_player_ids: [...aliveSet],
			phase,
			day_number: dayNumber,
			players: game.players.map((p) => ({
				name: p.name,
				role: p.role!,
				is_alive: aliveSet.has(p.name)
			}))
		};
	}

	// Events for display: replay slice, full history, or live (buffered)
	let displayEvents = $derived.by(() => {
		if (isReplaying) return historyEvents.slice(0, replayIndex + 1);
		if (viewingGameId) return historyEvents;
		return displayedLiveEvents; // Use buffered events instead of raw $events
	});

	// Snapshot for display: reconstructed history or live
	let displaySnapshot = $derived.by(() => {
		if (!viewingGameId) return $snapshot;
		const idx = isReplaying ? replayIndex : historyEvents.length - 1;
		return reconstructSnapshot(historyGame, historyEvents, idx);
	});

	// Speaker derived from display events (for both history/replay and buffered live mode)
	let displaySpeaker = $derived.by(() => {
		const evts = displayEvents;
		const lastSpeech = [...evts].reverse().find((e) => e.type === 'speech');
		if (!lastSpeech) return null;
		const payload = lastSpeech.payload as { content?: string; player_name?: string; audio_base64?: string };
		// Use player_name as playerId since RoundTable uses names as player IDs
		return {
			playerId: payload.player_name || null,
			playerName: payload.player_name || 'Unknown',
			content: payload.content || '',
			audioBase64: payload.audio_base64 || null
		};
	});

	// Votes derived from display events (for both history/replay and buffered live mode)
	let displayVotes = $derived.by(() => {
		const votes = new Map<string, string>();
		let lastPhaseChangeIndex = -1;
		displayEvents.forEach((e, i) => {
			if (e.type === 'phase_changed' || e.type === 'day_started' || e.type === 'night_started') {
				lastPhaseChangeIndex = i;
				votes.clear();
			}
			if (e.type === 'vote_cast' && i > lastPhaseChangeIndex) {
				// Use voter_name and target_name from payload since RoundTable uses names as player IDs
				const payload = e.payload as { voter_name?: string; target_name?: string };
				if (payload.voter_name && payload.target_name) {
					votes.set(payload.voter_name, payload.target_name);
				}
			}
		});
		return votes;
	});

	// Enriched players with alive status and roles for RoundTable
	let enrichedPlayers = $derived.by(() => {
		if (!series) return [];

		// Historical view: use reconstructed display snapshot
		if (viewingGameId && displaySnapshot?.players?.length) {
			return displaySnapshot.players.map((p) => ({
				id: p.name,
				name: p.name,
				role: p.role,
				is_alive: p.is_alive,
				playerId: playerIdByName.get(p.name)
			}));
		}

		// Live snapshot (existing logic)
		if ($snapshot?.players?.length) {
			return $snapshot.players.map((p) => ({
				id: p.name,
				name: p.name,
				role: p.role,
				is_alive: p.is_alive,
				playerId: playerIdByName.get(p.name)
			}));
		}

		// Fallback to series config if no game is running
		return series.config.players.map((p) => ({
			id: p.name,
			name: p.name,
			role: undefined,
			is_alive: true,
			playerId: playerIdByName.get(p.name)
		}));
	});

	// Cheatsheets for RoundTable - maps playerId -> cheatsheet
	// Uses the appropriate cache key based on viewing context (history vs live)
	let cheatsheetsForRoundTable = $derived.by(() => {
		const gameNumber = historyGame?.game_number;
		const result = new Map<string, Cheatsheet>();

		for (const player of seriesPlayers) {
			const cacheKey = gameNumber !== undefined ? `${player.id}:${gameNumber}` : player.id;
			const cheatsheet = cheatsheets.get(cacheKey);
			if (cheatsheet) {
				result.set(player.id, cheatsheet);
			}
		}

		return result;
	});

	// Helper to reset live state - called before loading a new series
	function resetLiveState() {
		liveEventQueue = [];
		displayedLiveEvents = [];
		liveWaitingForSpeech = false;
		lastProcessedEventCount = 0;
		liveInitialized = false;
		if (liveTimer) {
			clearTimeout(liveTimer);
			liveTimer = null;
		}
		speechBubbleKey++;
	}

	// Track if we've initialized for this series (plain variable, not reactive)
	// This prevents the effect from re-running when other state changes
	let initializedForSeries: string | null = null; // NOT $state - intentionally non-reactive

	$effect(() => {
		const seriesId = $page.params.id;
		if (seriesId && seriesId !== initializedForSeries) {
			initializedForSeries = seriesId;
			resetLiveState();
			loadData(seriesId);
			connect(seriesId);
		}
	});

	// Watch for new live events and queue them for buffered display
	$effect(() => {
		// Only buffer in live mode (not viewing history)
		if (viewingGameId) return;

		const allEvents = $events;
		const newEventCount = allEvents.length;

		// On first load (or when returning to live), show all existing events immediately
		if (!liveInitialized && newEventCount > 0) {
			displayedLiveEvents = [...allEvents];
			lastProcessedEventCount = newEventCount;
			liveInitialized = true;
			return;
		}

		// Queue any new events that arrived since last processed
		if (newEventCount > lastProcessedEventCount) {
			const newEvents = allEvents.slice(lastProcessedEventCount);

			// Check if a new game is starting - reset display state to show fresh animations
			const hasGameStarted = newEvents.some(e => e.type === 'game_started');
			if (hasGameStarted) {
				// Clear displayed events so animations restart fresh for the new game
				displayedLiveEvents = [];
				liveEventQueue = [];
				liveWaitingForSpeech = false;
				if (liveTimer) {
					clearTimeout(liveTimer);
					liveTimer = null;
				}
			}

			liveEventQueue = [...liveEventQueue, ...newEvents];
			lastProcessedEventCount = newEventCount;

			// Trigger processing if not already waiting
			if (!liveWaitingForSpeech && liveTimer === null) {
				processNextLiveEvent();
			}
		}
	});

	// Reset live buffering when switching to history view
	$effect(() => {
		if (viewingGameId) {
			// Entering history view - reset live state
			liveEventQueue = [];
			displayedLiveEvents = [];
			liveWaitingForSpeech = false;
			lastProcessedEventCount = 0;
			liveInitialized = false;
			if (liveTimer) {
				clearTimeout(liveTimer);
				liveTimer = null;
			}
		}
	});

	// Track last seen game event to refresh games list when new games start/end
	let lastSeenGameEventCount = $state(0);

	// Refresh games list when a game starts or ends
	$effect(() => {
		const allEvents = $events;
		if (allEvents.length <= lastSeenGameEventCount) return;

		const newEvents = allEvents.slice(lastSeenGameEventCount);
		const hasGameLifecycleEvent = newEvents.some(
			(e) => e.type === 'game_started' || e.type === 'game_ended'
		);

		lastSeenGameEventCount = allEvents.length;

		if (hasGameLifecycleEvent && series) {
			// Refresh games list
			fetchSeriesGames(series.id).then(async (res) => {
				if (res.ok) {
					games = await res.json();
				}
			});
		}
	});

	onDestroy(() => {
		disconnect();
		stopReplay();
		// Clean up live timer
		if (liveTimer) {
			clearTimeout(liveTimer);
			liveTimer = null;
		}
	});

	async function loadData(seriesId: string) {
		loading = true;
		error = null;
		try {
			const [seriesRes, gamesRes, playersRes] = await Promise.all([
				fetchSeriesById(seriesId),
				fetchSeriesGames(seriesId),
				fetchSeriesPlayers(seriesId)
			]);

			if (!seriesRes.ok) throw new Error('Failed to fetch series');
			if (!gamesRes.ok) throw new Error('Failed to fetch games');
			if (!playersRes.ok) throw new Error('Failed to fetch players');

			series = await seriesRes.json();
			games = await gamesRes.json();
			seriesPlayers = await playersRes.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	// Handle player hover - fetch cheatsheet on demand
	async function handlePlayerHover(playerId: string | null) {
		if (!playerId) {
			loadingCheatsheet = null;
			return;
		}

		// Determine cache key: include game number when viewing history
		// so we cache per-game cheatsheets separately
		const gameNumber = historyGame?.game_number;
		const cacheKey = gameNumber !== undefined ? `${playerId}:${gameNumber}` : playerId;

		// Already cached?
		if (cheatsheets.has(cacheKey)) {
			return;
		}

		// Fetch cheatsheet (pass game_number when viewing history for accurate replay)
		loadingCheatsheet = playerId;
		try {
			const res = await fetchPlayerCheatsheet(playerId, gameNumber);
			if (res.ok) {
				const data = await res.json();
				cheatsheets = new Map(cheatsheets).set(cacheKey, data.cheatsheet);
			}
		} catch (e) {
			console.error('Failed to fetch cheatsheet:', e);
		} finally {
			if (loadingCheatsheet === playerId) {
				loadingCheatsheet = null;
			}
		}
	}

	async function handleStop() {
		if (!series) return;
		try {
			const res = await stopSeries(series.id);
			if (!res.ok) throw new Error('Failed to stop series');
			await loadData(series.id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to stop';
		}
	}

	async function handleStart() {
		if (!series) return;
		try {
			const res = await startSeries(series.id);
			if (!res.ok) throw new Error('Failed to start series');
			await loadData(series.id);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to start';
		}
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'pending':
				return 'pending';
			case 'in_progress':
				return 'in-progress';
			case 'completed':
				return 'completed';
			case 'stop_requested':
				return 'warning';
			case 'stopped':
				return 'stopped';
			default:
				return '';
		}
	}

	function openDiffModal(playerName: string) {
		const playerId = playerIdByName.get(playerName);
		if (playerId) {
			diffModalPlayer = { id: playerId, name: playerName };
		}
	}

	function closeDiffModal() {
		diffModalPlayer = null;
	}

	// History viewing functions
	async function loadHistoryGame(gameId: string) {
		stopReplay();
		viewingGameId = gameId;
		historyLoading = true;

		try {
			const [gameRes, eventsRes] = await Promise.all([
				fetchGame(gameId),
				fetchGameEvents(gameId)
			]);

			if (!gameRes.ok || !eventsRes.ok) {
				throw new Error('Failed to load game history');
			}

			historyGame = await gameRes.json();
			historyEvents = await eventsRes.json();
		} catch (e) {
			console.error('Failed to load history:', e);
			closeHistoryView();
		} finally {
			historyLoading = false;
		}
	}

	function closeHistoryView() {
		stopReplay();
		viewingGameId = null;
		historyGame = null;
		historyEvents = [];

		// Catch up with live events that happened while viewing history
		// Show all current events immediately, then buffer any new ones
		const currentEvents = $events;
		displayedLiveEvents = [...currentEvents];
		lastProcessedEventCount = currentEvents.length;
		liveEventQueue = [];
		liveWaitingForSpeech = false;
		liveInitialized = true;
		if (liveTimer) {
			clearTimeout(liveTimer);
			liveTimer = null;
		}

		// Force SpeechBubble to re-render by incrementing a key
		// This ensures the typewriter restarts fresh when returning to live
		speechBubbleKey++;
	}

	// Live mode buffering functions
	function processNextLiveEvent() {
		if (liveEventQueue.length === 0 || liveWaitingForSpeech) {
			// Clear stale timer reference when queue is empty
			if (liveTimer) {
				clearTimeout(liveTimer);
				liveTimer = null;
			}
			return;
		}

		// Clear any pending timer
		if (liveTimer) {
			clearTimeout(liveTimer);
			liveTimer = null;
		}

		const nextEvent = liveEventQueue[0];
		displayedLiveEvents = [...displayedLiveEvents, nextEvent];
		liveEventQueue = liveEventQueue.slice(1);

		if (nextEvent.type === 'speech') {
			// Wait for speech streaming to complete (callback will trigger next)
			liveWaitingForSpeech = true;
		} else {
			// Non-speech event: short delay then process next
			liveTimer = setTimeout(processNextLiveEvent, NON_SPEECH_DELAY_MS);
		}
	}

	function handleLiveSpeechComplete() {
		if (!liveWaitingForSpeech) return;

		liveWaitingForSpeech = false;
		// Brief pause after speech before next event
		liveTimer = setTimeout(processNextLiveEvent, POST_SPEECH_DELAY_MS);
	}

	// Check if the current event at replayIndex is a speech event
	function isCurrentEventSpeech(): boolean {
		if (replayIndex >= historyEvents.length) return false;
		return historyEvents[replayIndex].type === 'speech';
	}

	// Advance to the next event in replay
	function advanceReplay() {
		if (!isReplaying) return;

		if (replayIndex >= historyEvents.length - 1) {
			// End replay but preserve position at final state
			isReplaying = false;
			waitingForSpeech = false;
			if (replayTimer) {
				clearTimeout(replayTimer);
				replayTimer = null;
			}
			return;
		}

		replayIndex++;

		// Schedule next advancement based on event type
		scheduleNextAdvance();
	}

	// Schedule the next event advancement based on current event type
	function scheduleNextAdvance() {
		if (!isReplaying) return;

		// Clear any pending timer
		if (replayTimer) {
			clearTimeout(replayTimer);
			replayTimer = null;
		}

		if (isCurrentEventSpeech()) {
			// Wait for speech streaming to complete (callback will trigger next advance)
			waitingForSpeech = true;
		} else {
			// Non-speech event: advance after short delay
			waitingForSpeech = false;
			replayTimer = setTimeout(advanceReplay, NON_SPEECH_DELAY_MS);
		}
	}

	// Called when speech bubble finishes streaming (replay mode)
	function handleReplaySpeechComplete() {
		if (!isReplaying || !waitingForSpeech) return;

		waitingForSpeech = false;
		// Brief pause after speech before next event
		replayTimer = setTimeout(advanceReplay, POST_SPEECH_DELAY_MS);
	}

	// Unified speech complete handler for RoundTable
	function handleSpeechComplete() {
		if (viewingGameId) {
			// History/replay mode
			handleReplaySpeechComplete();
		} else {
			// Live mode
			handleLiveSpeechComplete();
		}
	}

	function startReplay() {
		if (!viewingGameId || historyEvents.length === 0) return;

		// Clear any existing timer first to prevent memory leak
		if (replayTimer) {
			clearTimeout(replayTimer);
			replayTimer = null;
		}

		isReplaying = true;
		replayIndex = 0;
		waitingForSpeech = false;

		// Start the event-driven replay
		scheduleNextAdvance();
	}

	function stopReplay() {
		isReplaying = false;
		replayIndex = 0;
		waitingForSpeech = false;
		if (replayTimer) {
			clearTimeout(replayTimer);
			replayTimer = null;
		}
	}
</script>

<div class="page">
	{#if loading}
		<div class="loading-state">
			<div class="loading-spinner"></div>
			<span>Gathering intelligence...</span>
		</div>
	{:else if error}
		<div class="error-banner">
			<span class="error-icon">!</span>
			<span>{error}</span>
		</div>
	{:else if series}
		<div class="series-header">
			<div class="title-row">
				<a href="/" class="back-link">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M19 12H5M12 19l-7-7 7-7"/>
					</svg>
					<span>Back</span>
				</a>
				<div class="title-group">
					<h1>{series.name}</h1>
					<span class="badge {getStatusColor(currentSeriesStatus)}">{currentSeriesStatus.replace('_', ' ')}</span>
				</div>
			</div>

			<div class="actions">
				{#if currentSeriesStatus === 'pending'}
					<button onclick={handleStart}>Start Series</button>
				{:else if currentSeriesStatus === 'in_progress'}
					<button class="secondary" onclick={handleStop}>Stop After Current Phase</button>
				{:else if currentSeriesStatus === 'stop_requested'}
					<button class="secondary" disabled>Stopping...</button>
				{/if}
			</div>
		</div>

		{#if viewingGameId}
			<div class="history-bar">
				<div class="history-info">
					<span class="history-icon">📼</span>
					<span class="history-label">
						{#if historyLoading}
							Loading Game {historyGame?.game_number ?? ''}...
						{:else}
							Viewing Game {historyGame?.game_number}
						{/if}
					</span>
					{#if historyGame?.winner}
						<span class="badge {historyGame.winner}">{historyGame.winner} wins</span>
					{/if}
				</div>
				<div class="history-controls">
					{#if isReplaying}
						<span class="replay-progress">{replayIndex + 1} / {historyEvents.length}</span>
						<button class="small secondary" onclick={stopReplay}>Stop</button>
					{:else if historyEvents.length > 0}
						<button class="small" onclick={startReplay}>
							<span class="play-icon">▶</span> Replay
						</button>
					{/if}
					<button class="small secondary" onclick={closeHistoryView}>Back to Live</button>
				</div>
			</div>
		{:else}
			<div class="connection-bar" class:connected={$connectionState.connected}>
				<div class="connection-indicator">
					<span class="pulse-dot"></span>
					<span class="status-text">
						{$connectionState.connected ? 'Live' : 'Disconnected'}
					</span>
				</div>
				{#if $connectionState.connected && $connectionState.subscribedTo}
					<span class="subscribed-text">Receiving live updates</span>
				{/if}
				{#if liveEventQueue.length > 0}
					<span class="queue-indicator">
						<span class="queue-dot"></span>
						{liveEventQueue.length} queued
					</span>
				{/if}
				{#if $connectionState.error}
					<span class="error-text">{$connectionState.error}</span>
				{/if}
			</div>
		{/if}

		<div class="layout">
			<aside class="sidebar">
				<!-- Players Card -->
				<div class="sidebar-card">
					<div class="card-header">
						<span class="card-icon">
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
								<circle cx="9" cy="7" r="4"/>
								<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
								<path d="M16 3.13a4 4 0 0 1 0 7.75"/>
							</svg>
						</span>
						<h3>The Players</h3>
					</div>
					<div class="card-content">
						<div class="players-list">
							{#each series.config.players as player, i}
								{@const isAlive = !displaySnapshot || displaySnapshot.alive_player_ids.includes(player.name)}
								<button
									class="player-item"
									class:dead={!isAlive}
									onclick={() => openDiffModal(player.name)}
									title="View strategy evolution"
								>
									<div class="player-avatar">
										<span class="avatar-number">{i + 1}</span>
									</div>
									<div class="player-info">
										<span class="player-name">{player.name}</span>
										<span class="player-model">{player.model_name.split('/').pop()}</span>
									</div>
									{#if !isAlive}
										<span class="death-marker">R.I.P.</span>
									{/if}
									<span class="view-history-icon" aria-hidden="true">
										<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
											<path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
										</svg>
									</span>
								</button>
							{/each}
						</div>
					</div>
				</div>

				<!-- Games History Card -->
				<div class="sidebar-card">
					<div class="card-header">
						<span class="card-icon">
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
								<line x1="16" y1="2" x2="16" y2="6"/>
								<line x1="8" y1="2" x2="8" y2="6"/>
								<line x1="3" y1="10" x2="21" y2="10"/>
							</svg>
						</span>
						<h3>Games History</h3>
					</div>
					<div class="card-content">
						{#if games.length === 0}
							<div class="empty-games">
								<span>No games played yet</span>
							</div>
						{:else}
							<div class="games-list">
								{#each games as game}
									<button
										class="game-item"
										class:active={viewingGameId === game.id}
										onclick={() => loadHistoryGame(game.id)}
									>
										<div class="game-number">
											<span class="number">{game.game_number}</span>
										</div>
										<div class="game-details">
											<span class="badge {game.status}">{game.status}</span>
											{#if game.winner}
												<span class="badge {game.winner}">{game.winner} wins</span>
											{/if}
										</div>
									</button>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			</aside>

			<div class="main-content noir-theme">
				<div class="table-wrapper">
					<!-- Top-left: Progress -->
					<div class="table-overlay top-left">
						<span class="overlay-label">Game</span>
						<span class="overlay-value">
							{historyGame?.game_number ?? $seriesProgress?.game_number ?? series.current_game_number}/{$seriesProgress?.total_games ?? series.total_games}
						</span>
					</div>

					<!-- Top-right: Phase indicator (history) or LIVE indicator (current game) -->
					{#if viewingGameId && displaySnapshot}
						<div class="table-overlay top-right">
							<PhaseIndicator phase={displaySnapshot.phase} dayNumber={displaySnapshot.day_number} />
						</div>
					{:else if !viewingGameId && $snapshot}
						<div class="table-overlay top-right live-indicator">
							<span class="live-dot"></span>
							<span class="live-label">LIVE</span>
						</div>
					{/if}

					{#if displaySnapshot}
						<!-- Bottom-right: Alive count -->
						<div class="table-overlay bottom-right">
							<span class="overlay-label">Alive</span>
							<span class="overlay-value alive">{displaySnapshot.alive_player_ids.length}</span>
						</div>
					{/if}

					<RoundTable
						players={enrichedPlayers}
						currentSpeakerId={displaySpeaker?.playerId || null}
						speechContent={displaySpeaker?.content || null}
						speakerName={displaySpeaker?.playerName || null}
						speechAudioBase64={displaySpeaker?.audioBase64 || null}
						votes={displayVotes}
						showRoles={true}
						cheatsheets={cheatsheetsForRoundTable}
						{loadingCheatsheet}
						onPlayerHover={handlePlayerHover}
						onSpeechComplete={handleSpeechComplete}
						{speechBubbleKey}
					/>
				</div>

				<ChatLog events={displayEvents} />
			</div>
		</div>

		<!-- Cheatsheet Diff Modal -->
		{#if diffModalPlayer}
			<CheatsheetDiffModal
				playerId={diffModalPlayer.id}
				playerName={diffModalPlayer.name}
				visible={true}
				onClose={closeDiffModal}
			/>
		{/if}
	{/if}
</div>

<style>
	.page {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	/* ============================================
	   LOADING & ERROR STATES
	   ============================================ */
	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1.5rem;
		padding: 4rem;
		color: var(--text-secondary);
	}

	.loading-spinner {
		width: 48px;
		height: 48px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.error-banner {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem 1.5rem;
		background: rgba(196, 30, 58, 0.1);
		border: 1px solid var(--danger);
		border-radius: 4px;
		color: #f5a5b3;
	}

	.error-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		background: var(--danger);
		color: white;
		border-radius: 50%;
		font-weight: bold;
		font-size: 0.875rem;
	}

	/* ============================================
	   SERIES HEADER
	   ============================================ */
	.series-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1.5rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid var(--border);
	}

	.title-row {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.back-link {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--text-secondary);
		font-family: var(--font-body);
		font-size: 0.95rem;
		transition: color 0.2s ease;
	}

	.back-link:hover {
		color: var(--accent);
	}

	.back-link svg {
		width: 18px;
		height: 18px;
	}

	.title-group {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	h1 {
		font-family: var(--font-display);
		font-size: 2rem;
		font-weight: 600;
		background: linear-gradient(135deg, var(--text-cream) 0%, var(--accent) 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.actions {
		display: flex;
		gap: 0.75rem;
	}

	/* ============================================
	   CONNECTION BAR
	   ============================================ */
	.connection-bar {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		padding: 0.75rem 1.25rem;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 4px;
	}

	.connection-bar.connected {
		border-color: rgba(80, 200, 120, 0.3);
	}

	.connection-indicator {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.pulse-dot {
		width: 8px;
		height: 8px;
		background: var(--text-muted);
		border-radius: 50%;
	}

	.connection-bar.connected .pulse-dot {
		background: var(--success);
		animation: pulse 2s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}

	.status-text {
		font-family: var(--font-heading);
		font-size: 0.75rem;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-muted);
	}

	.connection-bar.connected .status-text {
		color: var(--success);
	}

	.subscribed-text {
		font-family: var(--font-body);
		font-size: 0.9rem;
		color: var(--text-secondary);
		font-style: italic;
	}

	.error-text {
		color: var(--danger);
		font-size: 0.9rem;
	}

	.queue-indicator {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-family: var(--font-body);
		font-size: 0.85rem;
		color: var(--accent);
		padding: 0.25rem 0.6rem;
		background: rgba(212, 175, 55, 0.1);
		border: 1px solid var(--accent-dim);
		border-radius: 12px;
	}

	.queue-dot {
		width: 6px;
		height: 6px;
		background: var(--accent);
		border-radius: 50%;
		animation: queuePulse 1s ease-in-out infinite;
	}

	@keyframes queuePulse {
		0%, 100% { transform: scale(1); opacity: 1; }
		50% { transform: scale(1.3); opacity: 0.7; }
	}

	/* ============================================
	   HISTORY BAR
	   ============================================ */
	.history-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.75rem 1.25rem;
		background: rgba(212, 175, 55, 0.08);
		border: 1px solid var(--accent-dim);
		border-radius: 4px;
	}

	.history-info {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.history-icon {
		font-size: 1.1rem;
	}

	.history-label {
		font-family: var(--font-heading);
		font-size: 0.85rem;
		color: var(--accent);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.history-controls {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	.replay-progress {
		font-family: var(--font-body);
		font-size: 0.85rem;
		color: var(--text-secondary);
		min-width: 70px;
		text-align: center;
	}

	button.small {
		padding: 0.4rem 0.8rem;
		font-size: 0.8rem;
	}

	.play-icon {
		font-size: 0.7rem;
		margin-right: 0.25rem;
	}

	/* ============================================
	   LAYOUT
	   ============================================ */
	.layout {
		display: grid;
		grid-template-columns: 320px 1fr;
		gap: 1.5rem;
	}

	@media (max-width: 1100px) {
		.layout {
			grid-template-columns: 1fr;
		}

		.sidebar {
			order: 2;
		}

		.main-content {
			order: 1;
		}
	}

	/* ============================================
	   SIDEBAR
	   ============================================ */
	.sidebar {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.sidebar-card {
		background: var(--bg-card);
		border: 1px solid var(--border-gold);
		border-radius: 4px;
		overflow: hidden;
		transition: all 0.3s ease;
	}

	.sidebar-card:hover {
		border-color: var(--accent-dim);
		box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
	}

	.card-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		background: rgba(0, 0, 0, 0.2);
		border-bottom: 1px solid var(--border);
	}

	.card-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 18px;
		height: 18px;
		color: var(--accent-dim);
	}

	.card-icon svg {
		width: 14px;
		height: 14px;
	}

	.card-header h3 {
		font-family: var(--font-heading);
		font-size: 0.7rem;
		font-weight: 400;
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-secondary);
	}

	.card-content {
		padding: 0.75rem 1rem;
	}

	/* Players List */
	.players-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.player-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 4px;
		transition: all 0.2s ease;
		cursor: pointer;
		width: 100%;
		text-align: left;
		font-family: inherit;
		font-size: inherit;
		position: relative;
	}

	.player-item:hover {
		border-color: var(--accent-dim);
		background: rgba(212, 175, 55, 0.05);
	}

	.player-item:hover .view-history-icon {
		opacity: 1;
	}

	.view-history-icon {
		position: absolute;
		right: 0.75rem;
		top: 50%;
		transform: translateY(-50%);
		width: 18px;
		height: 18px;
		color: var(--accent-dim);
		opacity: 0;
		transition: opacity 0.2s ease;
	}

	.view-history-icon svg {
		width: 100%;
		height: 100%;
	}

	.player-item.dead {
		opacity: 0.5;
		background: rgba(0, 0, 0, 0.3);
	}

	.player-avatar {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		background: linear-gradient(135deg, var(--accent-dim) 0%, var(--accent) 100%);
		border-radius: 50%;
		flex-shrink: 0;
	}

	.avatar-number {
		font-family: var(--font-heading);
		font-size: 0.85rem;
		color: var(--bg-primary);
	}

	.player-item.dead .player-avatar {
		background: var(--text-muted);
	}

	.player-info {
		flex: 1;
		min-width: 0;
	}

	.player-name {
		display: block;
		font-family: var(--font-body);
		font-size: 1rem;
		font-weight: 500;
		color: var(--text-cream);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.player-item.dead .player-name {
		text-decoration: line-through;
		color: var(--text-muted);
	}

	.player-model {
		display: block;
		font-family: var(--font-body);
		font-size: 0.75rem;
		color: var(--text-muted);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.death-marker {
		font-family: var(--font-display);
		font-size: 0.7rem;
		font-style: italic;
		color: var(--danger);
		opacity: 0.8;
	}

	/* Games List */
	.empty-games {
		text-align: center;
		padding: 1rem;
		color: var(--text-muted);
		font-style: italic;
	}

	.games-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		max-height: 200px;
		overflow-y: auto;
	}

	.game-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem 0.75rem;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 4px;
		cursor: pointer;
		width: 100%;
		text-align: left;
		font-family: inherit;
		font-size: inherit;
		transition: all 0.2s ease;
	}

	.game-item:hover {
		border-color: var(--accent-dim);
		background: rgba(212, 175, 55, 0.05);
	}

	.game-item.active {
		border-color: var(--accent);
		background: rgba(212, 175, 55, 0.1);
	}

	.game-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		background: var(--bg-secondary);
		border: 1px solid var(--border-gold);
		border-radius: 4px;
	}

	.game-number .number {
		font-family: var(--font-heading);
		font-size: 0.85rem;
		color: var(--accent-dim);
	}

	.game-details {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	/* ============================================
	   MAIN CONTENT
	   ============================================ */
	.main-content {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		min-height: calc(100vh - 300px);
		position: relative;
	}

	.table-wrapper {
		position: relative;
		flex-shrink: 0;
	}

	.table-overlay {
		position: absolute;
		z-index: 200;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.15rem;
		padding: 0.4rem 0.6rem;
		background: var(--bg-card-solid);
		opacity: 0.95;
		border: 1px solid var(--border-gold);
		border-radius: 4px;
		backdrop-filter: blur(4px);
		transition: background 0.4s ease, border-color 0.4s ease;
	}

	.table-overlay.top-left {
		top: 0.5rem;
		left: 0.5rem;
	}

	.table-overlay.top-right {
		top: 0.5rem;
		right: 0.5rem;
		padding: 0;
		background: transparent;
		border: none;
	}

	.table-overlay.top-right.live-indicator {
		flex-direction: row;
		gap: 0.5rem;
		padding: 0.5rem 0.8rem;
		background: var(--bg-card-solid);
		opacity: 0.98;
		border: 2px solid var(--success);
		border-radius: 4px;
		box-shadow: 0 0 15px rgba(80, 200, 120, 0.3);
	}

	.live-dot {
		width: 10px;
		height: 10px;
		background: var(--success);
		border-radius: 50%;
		animation: livePulse 1.5s ease-in-out infinite;
		box-shadow: 0 0 8px var(--success);
	}

	@keyframes livePulse {
		0%, 100% { opacity: 1; transform: scale(1); }
		50% { opacity: 0.6; transform: scale(0.9); }
	}

	.live-label {
		font-family: var(--font-heading);
		font-size: 0.85rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.15em;
		color: var(--success);
	}

	.table-overlay.bottom-right {
		bottom: 0.5rem;
		right: 0.5rem;
	}

	.overlay-label {
		font-family: var(--font-heading);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted);
	}

	.overlay-value {
		font-family: var(--font-display);
		font-size: 1rem;
		font-weight: 600;
		color: var(--accent);
	}

	.overlay-value.alive {
		color: var(--success);
	}

	/* ============================================
	   RESPONSIVE
	   ============================================ */
	@media (max-width: 768px) {
		.series-header {
			flex-direction: column;
			align-items: stretch;
		}

		.title-group {
			flex-wrap: wrap;
		}

		h1 {
			font-size: 1.5rem;
		}

		.connection-bar {
			flex-wrap: wrap;
		}
	}
</style>
