<script lang="ts">
	import { onMount } from 'svelte';
	import {
		fetchSeries,
		createSeries,
		startSeries,
		extractErrorDetails,
		fetchProvidersConfig,
		type ProviderConfig
	} from '$lib/api';
	import type { SeriesResponse } from '$lib/types';

	let seriesList = $state<SeriesResponse[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let showCreateForm = $state(false);

	// Provider config from backend
	let providerConfigs = $state<ProviderConfig[]>([]);
	let providersLoaded = $state(false);
	let providersError = $state<string | null>(null);

	// Form state
	let formName = $state('AI Mafia Tournament');
	let formTotalGames = $state(5);
	let formPlayers = $state([
		{ name: 'Alice', model_provider: 'openai_compatible', model_name: 'gpt-4o-mini', fixed_role: '', is_human: false },
		{ name: 'Bob', model_provider: 'openai_compatible', model_name: 'gpt-4o-mini', fixed_role: '', is_human: false },
		{ name: 'Charlie', model_provider: 'openai_compatible', model_name: 'gpt-4o-mini', fixed_role: '', is_human: false },
		{ name: 'Diana', model_provider: 'openai_compatible', model_name: 'gpt-4o-mini', fixed_role: '', is_human: false },
		{ name: 'Eve', model_provider: 'openai_compatible', model_name: 'gpt-4o-mini', fixed_role: '', is_human: false }
	]);

	onMount(async () => {
		await Promise.all([loadSeries(), loadProvidersConfig()]);
	});

	async function loadProvidersConfig() {
		try {
			const res = await fetchProvidersConfig();
			if (!res.ok) {
				const details = await extractErrorDetails(res);
				providersError = details || 'Failed to load provider configuration';
				return;
			}
			const data = await res.json();
			providerConfigs = data.providers;

			// Find first available provider and set as default for all players
			const firstAvailable = providerConfigs.find((p) => p.available);
			if (firstAvailable) {
				formPlayers = formPlayers.map((p) => ({
					...p,
					model_provider: firstAvailable.id,
					model_name: firstAvailable.default_model
				}));
			} else {
				providersError = 'No LLM providers configured. Add API keys in backend/.env';
			}
			providersLoaded = true;
		} catch (e) {
			providersError = e instanceof Error ? e.message : 'Failed to load provider configuration';
		}
	}

	async function loadSeries() {
		loading = true;
		error = null;
		try {
			const res = await fetchSeries();
			if (!res.ok) throw new Error('Failed to fetch series');
			seriesList = await res.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	async function handleCreateSeries() {
		try {
			const result = await createSeries({
				name: formName,
				total_games: formTotalGames,
				players: formPlayers.map((p) => ({
					name: p.name,
					model_provider: p.model_provider,
					model_name: p.model_name,
					fixed_role: p.fixed_role || undefined
				}))
			});
			if (!result.ok) {
				const details = await extractErrorDetails(result);
				console.error('[handleCreateSeries] Failed:', details);
				error = details || 'Failed to create series';
				return;
			}
			showCreateForm = false;
			await loadSeries();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to create series';
		}
	}

	async function handleStartSeries(seriesId: string) {
		try {
			const res = await startSeries(seriesId);
			if (!res.ok) {
				const details = await extractErrorDetails(res);
				throw new Error(details);
			}
			await loadSeries();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to start series';
		}
	}

	function addPlayer() {
		if (formPlayers.length < 7) {
			const firstAvailable = providerConfigs.find((p) => p.available);
			formPlayers = [
				...formPlayers,
				{
					name: `Player ${formPlayers.length + 1}`,
					model_provider: firstAvailable?.id ?? 'openai',
					model_name: firstAvailable?.default_model ?? '',
					fixed_role: '',
					is_human: false
				}
			];
		}
	}

	function removePlayer(index: number) {
		if (formPlayers.length > 5) {
			formPlayers = formPlayers.filter((_, i) => i !== index);
		}
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleString(undefined, {
			timeZoneName: 'short'
		});
	}

	// W&B Inference curated models
	const wandbModels = [
		{ id: 'qwen3-235b', name: 'Qwen3 235B', tag: 'Balanced', price: '$0.10/1M', recommended: true },
		{ id: 'llama-3.1-8b', name: 'Llama 3.1 8B', tag: 'Fast', price: '$0.22/1M' },
		{ id: 'deepseek-v3', name: 'DeepSeek V3', tag: 'Reasoning', price: '$1.14/1M' },
		{ id: 'llama-3.3-70b', name: 'Llama 3.3 70B', tag: 'Conversational', price: '$0.71/1M' },
		{ id: 'gpt-oss-20b', name: 'GPT OSS 20B', tag: 'Low Latency', price: '$0.05/1M' }
	];

	function getDefaultModelForProvider(providerId: string): string {
		const config = providerConfigs.find((p) => p.id === providerId);
		return config?.default_model ?? '';
	}

	function handleProviderChange(index: number, newProvider: string) {
		formPlayers[index].model_provider = newProvider;
		formPlayers[index].model_name = getDefaultModelForProvider(newProvider);
	}
</script>

<div class="page">
	<!-- Page Header with Art Deco styling -->
	<div class="page-header">
		<div class="header-content">
			<div class="title-section">
				<span class="title-decoration"></span>
				<h1>The Games</h1>
				<span class="title-decoration"></span>
			</div>
			<p class="subtitle">Where AI agents gather to deceive, deduce, and survive</p>
		</div>
		<button onclick={() => (showCreateForm = !showCreateForm)} class:secondary={showCreateForm}>
			{showCreateForm ? 'Cancel' : 'New Series'}
		</button>
	</div>

	{#if error || providersError}
		<div class="error-banner">
			<span class="error-icon">!</span>
			<span>{error || providersError}</span>
		</div>
	{/if}

	{#if showCreateForm}
		<div class="card create-form">
			<div class="form-header">
				<span class="form-diamond"></span>
				<h2>Establish New Series</h2>
				<span class="form-diamond"></span>
			</div>

			<div class="form-body">
				<div class="form-row">
					<div class="form-group">
						<label for="name">Series Name</label>
						<input id="name" type="text" bind:value={formName} placeholder="Enter a name..." />
					</div>

					<div class="form-group small">
						<label for="games">Total Games</label>
						<input id="games" type="number" min="1" max="100" bind:value={formTotalGames} />
					</div>
				</div>

				<div class="form-group">
					<div class="players-header">
						<span class="players-label">The Players</span>
						<span class="player-count">{formPlayers.length} / 7</span>
					</div>

					<div class="players-grid">
						{#each formPlayers as player, i}
							<div class="player-card" style="animation-delay: {i * 0.05}s">
								<div class="player-number">{i + 1}</div>
								<div class="player-fields">
									<input
										type="text"
										bind:value={player.name}
										placeholder="Name"
										class="player-name-input"
									/>
									<div class="player-model-row">
										<select
											value={player.model_provider}
											onchange={(e) => handleProviderChange(i, e.currentTarget.value)}
										>
											<option value="anthropic">Anthropic</option>
											<option value="openai">OpenAI</option>
											<option value="google">Google</option>
											<option value="openai_compatible">OpenAI Compatible</option>
											<option value="openrouter">OpenRouter</option>
											<option value="wandb">W&amp;B Inference</option>
										</select>
										{#if player.model_provider === 'wandb'}
											<select bind:value={player.model_name} class="model-input">
												{#each wandbModels as model}
													<option value={model.id}>
														{model.name} ({model.tag}) - {model.price}{model.recommended ? ' *' : ''}
													</option>
												{/each}
											</select>
										{:else}
											<input
												type="text"
												bind:value={player.model_name}
												placeholder="Model"
												class="model-input"
											/>
										{/if}
										<select bind:value={player.fixed_role} class="role-select">
											<option value="">Random</option>
											<option value="mafia">Mafia</option>
											<option value="doctor">Doctor</option>
											<option value="deputy">Deputy</option>
											<option value="townsperson">Townsperson</option>
										</select>
									</div>
								</div>
								{#if formPlayers.length > 5}
									<button class="remove-btn" onclick={() => removePlayer(i)} aria-label="Remove player {i + 1}">
										<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
											<path d="M18 6L6 18M6 6l12 12"/>
										</svg>
									</button>
								{/if}
							</div>
						{/each}
					</div>

					{#if formPlayers.length < 7}
						<button class="secondary add-player-btn" onclick={addPlayer}>
							<span class="add-icon">+</span>
							Add Player
						</button>
					{/if}
				</div>

				<div class="form-actions">
					<button onclick={handleCreateSeries}>
						Begin the Game
					</button>
				</div>
			</div>
		</div>
	{/if}

	{#if loading}
		<div class="loading-state">
			<div class="loading-spinner"></div>
			<span>Gathering intelligence...</span>
		</div>
	{:else if seriesList.length === 0}
		<div class="empty-state">
			<div class="empty-icon">
				<svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path d="M32 8L56 32L32 56L8 32L32 8Z" stroke="currentColor" stroke-width="2" opacity="0.3"/>
					<path d="M32 16L48 32L32 48L16 32L32 16Z" stroke="currentColor" stroke-width="2" opacity="0.5"/>
					<circle cx="32" cy="32" r="6" fill="currentColor" opacity="0.7"/>
				</svg>
			</div>
			<h3>No Games Yet</h3>
			<p>The tables are empty. Create a series to begin the deception.</p>
		</div>
	{:else}
		<div class="series-grid">
			{#each seriesList as series, i}
				<div class="series-card" style="animation-delay: {i * 0.1}s">
					<div class="card-corner top-left"></div>
					<div class="card-corner top-right"></div>
					<div class="card-corner bottom-left"></div>
					<div class="card-corner bottom-right"></div>

					<div class="series-header">
						<h3>{series.name}</h3>
						<span class="badge {series.status}">{series.status.replace('_', ' ')}</span>
					</div>

					<div class="series-stats">
						<div class="stat">
							<span class="stat-value">{series.current_game_number}</span>
							<span class="stat-label">of {series.total_games}</span>
						</div>
						<div class="stat-divider"></div>
						<div class="stat">
							<span class="stat-value">{series.config.players.length}</span>
							<span class="stat-label">players</span>
						</div>
					</div>

					<div class="series-players">
						{#each series.config.players.slice(0, 5) as player}
							<span class="player-chip">{player.name}</span>
						{/each}
						{#if series.config.players.length > 5}
							<span class="player-chip more">+{series.config.players.length - 5}</span>
						{/if}
					</div>

					<div class="series-meta">
						<span class="meta-date">{formatDate(series.created_at)}</span>
					</div>

					<div class="series-actions">
						{#if series.status === 'pending'}
							<button onclick={() => handleStartSeries(series.id)}>Start</button>
						{/if}
						<a href="/series/{series.id}" class="btn-view">
							<span>View</span>
							<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
								<path d="M5 12h14M12 5l7 7-7 7"/>
							</svg>
						</a>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.page {
		display: flex;
		flex-direction: column;
		gap: 2rem;
	}

	/* ============================================
	   PAGE HEADER
	   ============================================ */
	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 2rem;
		padding-bottom: 1.5rem;
		border-bottom: 1px solid var(--border);
	}

	.header-content {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.title-section {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.title-decoration {
		width: 40px;
		height: 2px;
		background: linear-gradient(90deg, var(--accent-dim), transparent);
	}

	.title-decoration:last-child {
		background: linear-gradient(90deg, transparent, var(--accent-dim));
	}

	h1 {
		font-family: var(--font-display);
		font-size: 2.5rem;
		font-weight: 600;
		background: linear-gradient(135deg, var(--text-cream) 0%, var(--accent) 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.subtitle {
		font-family: var(--font-body);
		font-size: 1.1rem;
		font-style: italic;
		color: var(--text-secondary);
		margin-left: 56px;
	}

	/* ============================================
	   ERROR BANNER
	   ============================================ */
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
	   CREATE FORM
	   ============================================ */
	.create-form {
		animation: fadeIn 0.3s ease-out;
	}

	.form-header {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		margin-bottom: 1.5rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid var(--border);
	}

	.form-diamond {
		width: 8px;
		height: 8px;
		background: var(--accent-dim);
		transform: rotate(45deg);
	}

	.form-header h2 {
		font-family: var(--font-display);
		font-size: 1.5rem;
		color: var(--text-gold);
	}

	.form-body {
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
	}

	.form-row {
		display: grid;
		grid-template-columns: 1fr 150px;
		gap: 1rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.form-group label,
	.players-label {
		font-family: var(--font-heading);
		font-size: 0.75rem;
		letter-spacing: 0.15em;
		text-transform: uppercase;
		color: var(--text-secondary);
	}

	.players-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.player-count {
		font-family: var(--font-heading);
		font-size: 0.75rem;
		letter-spacing: 0.1em;
		color: var(--accent-dim);
	}

	.players-grid {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.player-card {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 4px;
		animation: fadeIn 0.3s ease-out both;
	}

	.player-number {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		background: linear-gradient(135deg, var(--accent-dim) 0%, var(--accent) 100%);
		border-radius: 50%;
		font-family: var(--font-heading);
		font-size: 0.85rem;
		color: var(--bg-primary);
	}

	.player-fields {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.player-name-input {
		font-weight: 500;
	}

	.player-model-row {
		display: grid;
		grid-template-columns: 140px 1fr 110px;
		gap: 0.5rem;
	}

	.role-select {
		font-size: 0.875rem;
	}

	.model-input {
		font-size: 0.875rem;
	}

	.remove-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		padding: 0;
		background: transparent;
		border: 1px solid var(--border);
		color: var(--text-muted);
		box-shadow: none;
	}

	.remove-btn:hover {
		background: rgba(196, 30, 58, 0.1);
		border-color: var(--danger);
		color: var(--danger);
		box-shadow: none;
	}

	.remove-btn svg {
		width: 16px;
		height: 16px;
	}

	.add-player-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		margin-top: 0.5rem;
	}

	.add-icon {
		font-size: 1.25rem;
		line-height: 1;
	}

	.form-actions {
		display: flex;
		justify-content: flex-end;
		padding-top: 1rem;
		border-top: 1px solid var(--border);
	}

	/* ============================================
	   LOADING STATE
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

	/* ============================================
	   EMPTY STATE
	   ============================================ */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		padding: 4rem;
		text-align: center;
	}

	.empty-icon {
		width: 80px;
		height: 80px;
		color: var(--accent-dim);
		margin-bottom: 1rem;
	}

	.empty-icon svg {
		width: 100%;
		height: 100%;
	}

	.empty-state h3 {
		font-family: var(--font-display);
		font-size: 1.5rem;
		color: var(--text-cream);
	}

	.empty-state p {
		font-family: var(--font-body);
		font-size: 1.1rem;
		color: var(--text-secondary);
		font-style: italic;
	}

	/* ============================================
	   SERIES GRID
	   ============================================ */
	.series-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
		gap: 1.5rem;
	}

	.series-card {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
		padding: 1.75rem;
		background: var(--bg-card);
		border: 1px solid var(--border-gold);
		border-radius: 4px;
		box-shadow: var(--shadow-card);
		animation: fadeIn 0.4s ease-out both;
		transition: all 0.3s ease;
	}

	.series-card:hover {
		border-color: var(--accent);
		box-shadow:
			var(--shadow-card),
			0 0 30px rgba(212, 175, 55, 0.15);
		transform: translateY(-2px);
	}

	/* Art Deco Corner Accents */
	.card-corner {
		position: absolute;
		width: 16px;
		height: 16px;
		opacity: 0.5;
		transition: opacity 0.3s ease;
	}

	.series-card:hover .card-corner {
		opacity: 0.8;
	}

	.card-corner.top-left {
		top: 8px;
		left: 8px;
		border-top: 2px solid var(--accent-dim);
		border-left: 2px solid var(--accent-dim);
	}

	.card-corner.top-right {
		top: 8px;
		right: 8px;
		border-top: 2px solid var(--accent-dim);
		border-right: 2px solid var(--accent-dim);
	}

	.card-corner.bottom-left {
		bottom: 8px;
		left: 8px;
		border-bottom: 2px solid var(--accent-dim);
		border-left: 2px solid var(--accent-dim);
	}

	.card-corner.bottom-right {
		bottom: 8px;
		right: 8px;
		border-bottom: 2px solid var(--accent-dim);
		border-right: 2px solid var(--accent-dim);
	}

	.series-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
	}

	.series-header h3 {
		font-family: var(--font-display);
		font-size: 1.35rem;
		font-weight: 600;
		color: var(--text-cream);
		line-height: 1.3;
	}

	.series-stats {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		padding: 1rem 0;
		border-top: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
	}

	.stat {
		display: flex;
		align-items: baseline;
		gap: 0.35rem;
	}

	.stat-value {
		font-family: var(--font-display);
		font-size: 1.75rem;
		font-weight: 600;
		color: var(--accent);
	}

	.stat-label {
		font-family: var(--font-body);
		font-size: 0.95rem;
		color: var(--text-muted);
	}

	.stat-divider {
		width: 1px;
		height: 32px;
		background: var(--border);
	}

	.series-players {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.player-chip {
		padding: 0.35rem 0.75rem;
		background: rgba(212, 175, 55, 0.08);
		border: 1px solid var(--border);
		border-radius: 2px;
		font-family: var(--font-body);
		font-size: 0.9rem;
		color: var(--text-secondary);
	}

	.player-chip.more {
		background: rgba(212, 175, 55, 0.15);
		border-color: var(--accent-dim);
		color: var(--accent-dim);
	}

	.series-meta {
		display: flex;
		align-items: center;
	}

	.meta-date {
		font-family: var(--font-body);
		font-size: 0.875rem;
		color: var(--text-muted);
		font-style: italic;
	}

	.series-actions {
		display: flex;
		gap: 0.75rem;
		margin-top: auto;
	}

	.btn-view {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		flex: 1;
		padding: 0.75rem 1.5rem;
		background: transparent;
		border: 1px solid var(--border-gold);
		border-radius: 2px;
		font-family: var(--font-heading);
		font-size: 0.9rem;
		letter-spacing: 0.15em;
		text-transform: uppercase;
		color: var(--text-gold);
		text-decoration: none;
		transition: all 0.3s ease;
	}

	.btn-view:hover {
		background: rgba(212, 175, 55, 0.1);
		border-color: var(--accent);
		box-shadow: 0 0 15px rgba(212, 175, 55, 0.15);
		color: var(--accent-hover);
	}

	.btn-view svg {
		width: 16px;
		height: 16px;
		transition: transform 0.2s ease;
	}

	.btn-view:hover svg {
		transform: translateX(3px);
	}

	/* ============================================
	   ANIMATIONS
	   ============================================ */
	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* ============================================
	   RESPONSIVE
	   ============================================ */
	@media (max-width: 768px) {
		.page-header {
			flex-direction: column;
			align-items: stretch;
		}

		.title-decoration {
			display: none;
		}

		.subtitle {
			margin-left: 0;
		}

		.form-row {
			grid-template-columns: 1fr;
		}

		.player-model-row {
			grid-template-columns: 1fr 1fr;
		}

		.role-select {
			grid-column: span 2;
		}

		.series-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
