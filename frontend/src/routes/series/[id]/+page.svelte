<script lang="ts">
	import { onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { fetchSeriesById, fetchSeriesGames, stopSeries, startSeries } from '$lib/api';
	import {
		connect,
		disconnect,
		connectionState,
		events,
		snapshot,
		seriesProgress,
		currentSpeaker,
		currentVotes
	} from '$lib/websocket';
	import type { SeriesResponse } from '$lib/types';
	import RoundTable from '$lib/components/RoundTable.svelte';
	import ChatLog from '$lib/components/ChatLog.svelte';
	import PhaseIndicator from '$lib/components/PhaseIndicator.svelte';

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

	// Player name lookup from series config
	let playerNames = $derived.by(() => {
		if (!series) return new Map<string, string>();
		const map = new Map<string, string>();
		// We'll need to fetch player IDs - for now use names directly
		return map;
	});

	// Enriched players with alive status and roles for RoundTable
	let enrichedPlayers = $derived.by(() => {
		if (!series) return [];

		// If we have a snapshot with players, use that (includes roles)
		if ($snapshot?.players?.length) {
			return $snapshot.players.map((p) => ({
				id: p.name,
				name: p.name,
				role: p.role,
				is_alive: p.is_alive
			}));
		}

		// Fallback to series config if no game is running
		return series.config.players.map((p) => ({
			id: p.name,
			name: p.name,
			role: undefined,
			is_alive: true
		}));
	});

	$effect(() => {
		const seriesId = $page.params.id;
		if (seriesId) {
			loadData(seriesId);
			connect(seriesId);
		}
	});

	onDestroy(() => {
		disconnect();
	});

	async function loadData(seriesId: string) {
		loading = true;
		error = null;
		try {
			const [seriesRes, gamesRes] = await Promise.all([
				fetchSeriesById(seriesId),
				fetchSeriesGames(seriesId)
			]);

			if (!seriesRes.ok) throw new Error('Failed to fetch series');
			if (!gamesRes.ok) throw new Error('Failed to fetch games');

			series = await seriesRes.json();
			games = await gamesRes.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
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
			default:
				return '';
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
					<span class="badge {getStatusColor(series.status)}">{series.status.replace('_', ' ')}</span>
				</div>
			</div>

			<div class="actions">
				{#if series.status === 'pending'}
					<button onclick={handleStart}>Start Series</button>
				{:else if series.status === 'in_progress'}
					<button class="secondary" onclick={handleStop}>Stop After Current Game</button>
				{/if}
			</div>
		</div>

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
			{#if $connectionState.error}
				<span class="error-text">{$connectionState.error}</span>
			{/if}
		</div>

		<div class="layout">
			<aside class="sidebar">
				<!-- Progress Card -->
				<div class="sidebar-card">
					<div class="card-header">
						<span class="card-icon">
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<circle cx="12" cy="12" r="10"/>
								<path d="M12 6v6l4 2"/>
							</svg>
						</span>
						<h3>Progress</h3>
					</div>
					<div class="card-content">
						{#if $seriesProgress}
							<div class="progress-display">
								<div class="progress-numbers">
									<span class="current">{$seriesProgress.game_number}</span>
									<span class="separator">/</span>
									<span class="total">{$seriesProgress.total_games}</span>
								</div>
								<div class="progress-bar">
									<div
										class="progress-fill"
										style="width: {($seriesProgress.game_number / $seriesProgress.total_games) * 100}%"
									></div>
								</div>
								<span class="progress-label">Games Played</span>
							</div>
						{:else}
							<div class="progress-display">
								<div class="progress-numbers">
									<span class="current">{series.current_game_number}</span>
									<span class="separator">/</span>
									<span class="total">{series.total_games}</span>
								</div>
								<div class="progress-bar">
									<div
										class="progress-fill"
										style="width: {(series.current_game_number / series.total_games) * 100}%"
									></div>
								</div>
								<span class="progress-label">Games Played</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Current Game Card -->
				{#if $snapshot}
					<div class="sidebar-card game-card">
						<div class="card-header">
							<span class="card-icon">
								<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M12 2L2 7l10 5 10-5-10-5z"/>
									<path d="M2 17l10 5 10-5"/>
									<path d="M2 12l10 5 10-5"/>
								</svg>
							</span>
							<h3>Current Game</h3>
						</div>
						<div class="card-content">
							<div class="game-stats">
								<div class="game-stat">
									<span class="stat-label">Phase</span>
									<span class="badge {$snapshot.phase}">{$snapshot.phase}</span>
								</div>
								<div class="game-stat">
									<span class="stat-label">Day</span>
									<span class="stat-value">{$snapshot.day_number}</span>
								</div>
								<div class="game-stat">
									<span class="stat-label">Alive</span>
									<span class="stat-value alive">{$snapshot.alive_player_ids.length}</span>
								</div>
							</div>
						</div>
					</div>
				{/if}

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
								{@const isAlive = !$snapshot || $snapshot.alive_player_ids.includes(player.name)}
								<div class="player-item" class:dead={!isAlive}>
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
								</div>
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
									<div class="game-item">
										<div class="game-number">
											<span class="number">{game.game_number}</span>
										</div>
										<div class="game-details">
											<span class="badge {game.status}">{game.status}</span>
											{#if game.winner}
												<span class="badge {game.winner}">{game.winner} wins</span>
											{/if}
										</div>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			</aside>

			<div class="main-content noir-theme">
				{#if $snapshot}
					<div class="phase-row">
						<PhaseIndicator phase={$snapshot.phase} dayNumber={$snapshot.day_number} />
					</div>
				{/if}

				<RoundTable
					players={enrichedPlayers}
					currentSpeakerId={$currentSpeaker?.playerId || null}
					speechContent={$currentSpeaker?.content || null}
					speakerName={$currentSpeaker?.playerName || null}
					votes={$currentVotes}
					showRoles={true}
				/>

				<ChatLog events={$events} />
			</div>
		</div>
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
		background: linear-gradient(135deg, #1a1917 0%, #141412 100%);
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
		gap: 0.75rem;
		padding: 1rem 1.25rem;
		background: rgba(0, 0, 0, 0.2);
		border-bottom: 1px solid var(--border);
	}

	.card-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		color: var(--accent-dim);
	}

	.card-icon svg {
		width: 18px;
		height: 18px;
	}

	.card-header h3 {
		font-family: var(--font-heading);
		font-size: 0.8rem;
		font-weight: 400;
		letter-spacing: 0.15em;
		text-transform: uppercase;
		color: var(--text-secondary);
	}

	.card-content {
		padding: 1.25rem;
	}

	/* Progress Display */
	.progress-display {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		align-items: center;
		text-align: center;
	}

	.progress-numbers {
		display: flex;
		align-items: baseline;
		gap: 0.25rem;
	}

	.progress-numbers .current {
		font-family: var(--font-display);
		font-size: 2.5rem;
		font-weight: 600;
		color: var(--accent);
	}

	.progress-numbers .separator {
		font-family: var(--font-body);
		font-size: 1.5rem;
		color: var(--text-muted);
	}

	.progress-numbers .total {
		font-family: var(--font-display);
		font-size: 1.5rem;
		color: var(--text-secondary);
	}

	.progress-bar {
		width: 100%;
		height: 6px;
		background: var(--bg-primary);
		border-radius: 3px;
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: linear-gradient(90deg, var(--accent-dim), var(--accent));
		border-radius: 3px;
		transition: width 0.5s ease;
	}

	.progress-label {
		font-family: var(--font-body);
		font-size: 0.85rem;
		color: var(--text-muted);
		font-style: italic;
	}

	/* Game Stats */
	.game-stats {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.game-stat {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.game-stat .stat-label {
		font-family: var(--font-body);
		font-size: 0.95rem;
		color: var(--text-secondary);
	}

	.game-stat .stat-value {
		font-family: var(--font-display);
		font-size: 1.1rem;
		font-weight: 600;
		color: var(--text-cream);
	}

	.game-stat .stat-value.alive {
		color: var(--success);
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
	}

	.player-item:hover {
		border-color: var(--accent-dim);
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

	.phase-row {
		display: flex;
		justify-content: center;
		padding: 0.5rem 0;
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
