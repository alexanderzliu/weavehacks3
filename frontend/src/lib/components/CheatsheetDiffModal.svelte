<script lang="ts">
	import { fetchCheatsheetHistory } from '$lib/api';
	import type { CheatsheetVersion, CheatsheetItem } from '$lib/types';

	interface Props {
		playerId: string;
		playerName: string;
		visible: boolean;
		onClose: () => void;
	}

	let { playerId, playerName, visible, onClose }: Props = $props();

	let history = $state<CheatsheetVersion[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);

	// Selected versions for comparison
	let leftVersionIndex = $state(0);
	let rightVersionIndex = $state(1);

	// Fetch history when modal opens
	$effect(() => {
		if (visible && playerId) {
			loadHistory();
		}
	});

	async function loadHistory() {
		loading = true;
		error = null;
		try {
			const res = await fetchCheatsheetHistory(playerId);
			if (!res.ok) throw new Error('Failed to fetch history');
			history = await res.json();
			// Default to comparing the two most recent versions
			if (history.length >= 2) {
				leftVersionIndex = history.length - 2;
				rightVersionIndex = history.length - 1;
			} else if (history.length === 1) {
				leftVersionIndex = 0;
				rightVersionIndex = 0;
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	// Compute diff between two versions
	interface DiffResult {
		added: CheatsheetItem[];
		removed: CheatsheetItem[];
		modified: Array<{ old: CheatsheetItem; new: CheatsheetItem }>;
		unchanged: CheatsheetItem[];
	}

	// Create a content key for matching items without relying on IDs
	function getContentKey(item: CheatsheetItem): string {
		return `${item.category}::${item.content}`;
	}

	let diff = $derived.by((): DiffResult => {
		if (history.length < 1) return { added: [], removed: [], modified: [], unchanged: [] };

		const leftVersion = history[leftVersionIndex];
		const rightVersion = history[rightVersionIndex];

		if (!leftVersion || !rightVersion) {
			return { added: [], removed: [], modified: [], unchanged: [] };
		}

		// If comparing same version, everything is unchanged
		if (leftVersionIndex === rightVersionIndex) {
			return { added: [], removed: [], modified: [], unchanged: [...leftVersion.items] };
		}

		const added: CheatsheetItem[] = [];
		const removed: CheatsheetItem[] = [];
		const modified: Array<{ old: CheatsheetItem; new: CheatsheetItem }> = [];
		const unchanged: CheatsheetItem[] = [];

		// Track which items have been matched
		const matchedLeftIds = new Set<string>();
		const matchedRightIds = new Set<string>();

		// First pass: match by ID
		const leftById = new Map(leftVersion.items.map((item) => [item.id, item]));
		const rightById = new Map(rightVersion.items.map((item) => [item.id, item]));

		for (const [id, rightItem] of rightById) {
			const leftItem = leftById.get(id);
			if (leftItem) {
				matchedLeftIds.add(id);
				matchedRightIds.add(id);
				if (
					leftItem.content !== rightItem.content ||
					Math.abs(leftItem.helpfulness_score - rightItem.helpfulness_score) > 0.01
				) {
					modified.push({ old: leftItem, new: rightItem });
				} else {
					unchanged.push(rightItem);
				}
			}
		}

		// Second pass: match unmatched items by content
		const unmatchedLeft = leftVersion.items.filter((item) => !matchedLeftIds.has(item.id));
		const unmatchedRight = rightVersion.items.filter((item) => !matchedRightIds.has(item.id));

		// Create content-based lookup for unmatched left items
		const leftByContent = new Map<string, CheatsheetItem>();
		for (const item of unmatchedLeft) {
			leftByContent.set(getContentKey(item), item);
		}

		for (const rightItem of unmatchedRight) {
			const contentKey = getContentKey(rightItem);
			const leftItem = leftByContent.get(contentKey);

			if (leftItem) {
				// Same content - check if score changed
				leftByContent.delete(contentKey);
				matchedLeftIds.add(leftItem.id);

				if (Math.abs(leftItem.helpfulness_score - rightItem.helpfulness_score) > 0.01) {
					modified.push({ old: leftItem, new: rightItem });
				} else {
					unchanged.push(rightItem);
				}
			} else {
				// Truly new item
				added.push(rightItem);
			}
		}

		// Remaining unmatched left items are removed
		for (const [, item] of leftByContent) {
			removed.push(item);
		}

		return { added, removed, modified, unchanged };
	});

	function formatScore(score: number): string {
		return `${Math.round(score * 100)}%`;
	}

	function getScoreChange(oldScore: number, newScore: number): string {
		const diff = Math.round((newScore - oldScore) * 100);
		if (diff > 0) return `+${diff}%`;
		if (diff < 0) return `${diff}%`;
		return '';
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			onClose();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			onClose();
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if visible}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div class="modal-backdrop" onclick={handleBackdropClick}>
		<div class="modal">
			<header class="modal-header">
				<div class="header-content">
					<h2>{playerName}'s Strategy Evolution</h2>
					<span class="subtitle">Cheatsheet History</span>
				</div>
				<button class="close-btn" onclick={onClose} aria-label="Close">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M18 6L6 18M6 6l12 12" />
					</svg>
				</button>
			</header>

			{#if loading}
				<div class="loading-state">
					<div class="loading-spinner"></div>
					<span>Loading strategy history...</span>
				</div>
			{:else if error}
				<div class="error-state">
					<span class="error-icon">!</span>
					<span>{error}</span>
				</div>
			{:else if history.length === 0}
				<div class="empty-state">
					<span class="empty-icon">📋</span>
					<span>No strategy versions recorded yet</span>
				</div>
			{:else if history.length === 1}
				<div class="single-version">
					<p>Only one version exists (v{history[0].version})</p>
					<div class="items-list">
						{#each history[0].items as item}
							<div class="item unchanged">
								<span class="item-category">{item.category}</span>
								<span class="item-content">{item.content}</span>
								<span class="item-score">{formatScore(item.helpfulness_score)}</span>
							</div>
						{/each}
					</div>
				</div>
			{:else}
				<!-- Version selectors -->
				<div class="version-selectors">
					<div class="selector">
						<label for="left-version">From:</label>
						<select id="left-version" bind:value={leftVersionIndex}>
							{#each history as version, i}
								<option value={i}>
									v{version.version}
									{version.created_after_game !== null
										? `(after game ${version.created_after_game})`
										: '(initial)'}
								</option>
							{/each}
						</select>
					</div>
					<div class="arrow">→</div>
					<div class="selector">
						<label for="right-version">To:</label>
						<select id="right-version" bind:value={rightVersionIndex}>
							{#each history as version, i}
								<option value={i}>
									v{version.version}
									{version.created_after_game !== null
										? `(after game ${version.created_after_game})`
										: '(initial)'}
								</option>
							{/each}
						</select>
					</div>
				</div>

				<!-- Diff view -->
				<div class="diff-container">
					<!-- Summary stats -->
					<div class="diff-summary">
						{#if diff.added.length > 0}
							<span class="stat added">+{diff.added.length} added</span>
						{/if}
						{#if diff.removed.length > 0}
							<span class="stat removed">-{diff.removed.length} removed</span>
						{/if}
						{#if diff.modified.length > 0}
							<span class="stat modified">~{diff.modified.length} modified</span>
						{/if}
						{#if diff.added.length === 0 && diff.removed.length === 0 && diff.modified.length === 0}
							<span class="stat unchanged">No changes</span>
						{/if}
					</div>

					<!-- Side by side panels -->
					<div class="diff-panels">
						<div class="panel left">
							<div class="panel-header">
								<span class="version-label">v{history[leftVersionIndex]?.version ?? 0}</span>
								<span class="version-meta">
									{history[leftVersionIndex]?.created_after_game !== null
										? `After game ${history[leftVersionIndex]?.created_after_game}`
										: 'Initial'}
								</span>
							</div>
							<div class="panel-content">
								<!-- Removed items -->
								{#each diff.removed as item}
									<div class="item removed">
										<div class="item-header">
											<span class="item-category">{item.category}</span>
											<div class="item-meta">
												<span class="item-score">{formatScore(item.helpfulness_score)}</span>
												<span class="change-indicator">Removed</span>
											</div>
										</div>
										<span class="item-content">{item.content}</span>
									</div>
								{/each}

								<!-- Modified items (old version) -->
								{#each diff.modified as mod}
									<div class="item modified">
										<div class="item-header">
											<span class="item-category">{mod.old.category}</span>
											<span class="item-score">{formatScore(mod.old.helpfulness_score)}</span>
										</div>
										<span class="item-content">{mod.old.content}</span>
									</div>
								{/each}

								<!-- Unchanged items -->
								{#each diff.unchanged as item}
									<div class="item unchanged">
										<div class="item-header">
											<span class="item-category">{item.category}</span>
											<span class="item-score">{formatScore(item.helpfulness_score)}</span>
										</div>
										<span class="item-content">{item.content}</span>
									</div>
								{/each}
							</div>
						</div>

						<div class="panel right">
							<div class="panel-header">
								<span class="version-label">v{history[rightVersionIndex]?.version ?? 0}</span>
								<span class="version-meta">
									{history[rightVersionIndex]?.created_after_game !== null
										? `After game ${history[rightVersionIndex]?.created_after_game}`
										: 'Initial'}
								</span>
							</div>
							<div class="panel-content">
								<!-- Added items -->
								{#each diff.added as item}
									<div class="item added">
										<div class="item-header">
											<span class="item-category">{item.category}</span>
											<div class="item-meta">
												<span class="item-score">{formatScore(item.helpfulness_score)}</span>
												<span class="change-indicator">New</span>
											</div>
										</div>
										<span class="item-content">{item.content}</span>
										{#if item.source_event}
											<div class="source-citation">
												<span class="citation-icon">💡</span>
												<span class="citation-text">{item.source_event}</span>
											</div>
										{/if}
									</div>
								{/each}

								<!-- Modified items (new version) -->
								{#each diff.modified as mod}
									{@const scoreChange = getScoreChange(
										mod.old.helpfulness_score,
										mod.new.helpfulness_score
									)}
									{@const contentChanged = mod.old.content !== mod.new.content}
									<div class="item modified">
										<div class="item-header">
											<span class="item-category">{mod.new.category}</span>
											<div class="item-meta">
												<span class="item-score">
													{formatScore(mod.new.helpfulness_score)}
													{#if scoreChange}
														<span
															class="score-change"
															class:positive={mod.new.helpfulness_score > mod.old.helpfulness_score}
															class:negative={mod.new.helpfulness_score < mod.old.helpfulness_score}
														>
															{scoreChange}
														</span>
													{/if}
												</span>
												{#if contentChanged}
													<span class="change-indicator">Updated</span>
												{:else if scoreChange}
													<span class="change-indicator">Score</span>
												{/if}
											</div>
										</div>
										<span class="item-content">{mod.new.content}</span>
										{#if mod.new.source_event}
											<div class="source-citation">
												<span class="citation-icon">💡</span>
												<span class="citation-text">{mod.new.source_event}</span>
											</div>
										{/if}
									</div>
								{/each}

								<!-- Unchanged items -->
								{#each diff.unchanged as item}
									<div class="item unchanged">
										<div class="item-header">
											<span class="item-category">{item.category}</span>
											<span class="item-score">{formatScore(item.helpfulness_score)}</span>
										</div>
										<span class="item-content">{item.content}</span>
									</div>
								{/each}
							</div>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.7);
		backdrop-filter: blur(4px);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 10000;
		animation: fadeIn 0.2s ease-out;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	.modal {
		background: var(--bg-card, linear-gradient(135deg, #1a1917 0%, #0f0e0d 100%));
		border: 1px solid var(--noir-gold-dim, #a68829);
		border-radius: 8px;
		width: 90vw;
		max-width: 1100px;
		max-height: 85vh;
		display: flex;
		flex-direction: column;
		box-shadow:
			0 20px 60px rgba(0, 0, 0, 0.7),
			0 0 40px var(--accent-glow, rgba(212, 175, 55, 0.1));
		animation: slideIn 0.3s ease-out;
		transition: background 0.4s ease, border-color 0.4s ease;
	}

	@keyframes slideIn {
		from {
			opacity: 0;
			transform: translateY(-20px) scale(0.98);
		}
		to {
			opacity: 1;
			transform: translateY(0) scale(1);
		}
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 1.25rem 1.5rem;
		border-bottom: 1px solid rgba(212, 175, 55, 0.2);
		background: rgba(0, 0, 0, 0.3);
	}

	.header-content h2 {
		font-family: 'Playfair Display', serif;
		font-size: 1.35rem;
		font-weight: 600;
		color: var(--noir-gold, #d4af37);
		margin: 0;
		letter-spacing: 0.02em;
	}

	.subtitle {
		font-family: 'Bebas Neue', sans-serif;
		font-size: 0.75rem;
		color: var(--text-muted, #6a5d4d);
		text-transform: uppercase;
		letter-spacing: 0.15em;
	}

	.close-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		background: transparent;
		border: 1px solid var(--border, #3a3632);
		border-radius: 4px;
		color: var(--text-muted, #6a5d4d);
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.close-btn:hover {
		border-color: var(--noir-gold-dim, #a68829);
		color: var(--noir-gold, #d4af37);
	}

	.close-btn svg {
		width: 18px;
		height: 18px;
	}

	/* Loading / Error / Empty states */
	.loading-state,
	.error-state,
	.empty-state,
	.single-version {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		padding: 3rem;
		color: var(--text-muted, #6a5d4d);
		text-align: center;
	}

	.loading-spinner {
		width: 32px;
		height: 32px;
		border: 2px solid rgba(212, 175, 55, 0.2);
		border-top-color: var(--noir-gold, #d4af37);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.error-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		background: var(--danger, #c41e3a);
		color: white;
		border-radius: 50%;
		font-weight: bold;
	}

	.empty-icon {
		font-size: 2rem;
		opacity: 0.6;
	}

	/* Version selectors */
	.version-selectors {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1.5rem;
		padding: 1rem 1.5rem;
		background: rgba(0, 0, 0, 0.2);
		border-bottom: 1px solid rgba(212, 175, 55, 0.1);
	}

	.selector {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.selector label {
		font-family: 'Bebas Neue', sans-serif;
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-muted, #6a5d4d);
	}

	.selector select {
		font-family: 'Cormorant Garamond', serif;
		font-size: 0.95rem;
		padding: 0.4rem 0.75rem;
		background: var(--bg-primary, #141412);
		border: 1px solid var(--border, #3a3632);
		border-radius: 4px;
		color: var(--text-cream, #f5f0e6);
		cursor: pointer;
	}

	.selector select:hover {
		border-color: var(--noir-gold-dim, #a68829);
	}

	.arrow {
		font-size: 1.25rem;
		color: var(--noir-gold-dim, #a68829);
	}

	/* Diff container */
	.diff-container {
		flex: 1;
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	.diff-summary {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		padding: 0.75rem;
		background: rgba(0, 0, 0, 0.15);
		border-bottom: 1px solid rgba(212, 175, 55, 0.1);
	}

	.stat {
		font-family: 'Bebas Neue', sans-serif;
		font-size: 0.8rem;
		padding: 0.25rem 0.6rem;
		border-radius: 3px;
		letter-spacing: 0.05em;
	}

	.stat.added {
		background: rgba(80, 200, 120, 0.15);
		color: #50c878;
		border: 1px solid rgba(80, 200, 120, 0.3);
	}

	.stat.removed {
		background: rgba(196, 30, 58, 0.15);
		color: #f5a5b3;
		border: 1px solid rgba(196, 30, 58, 0.3);
	}

	.stat.modified {
		background: rgba(212, 175, 55, 0.15);
		color: var(--noir-gold, #d4af37);
		border: 1px solid rgba(212, 175, 55, 0.3);
	}

	.stat.unchanged {
		background: rgba(100, 100, 100, 0.15);
		color: var(--text-muted, #6a5d4d);
		border: 1px solid rgba(100, 100, 100, 0.3);
	}

	/* Diff panels */
	.diff-panels {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1px;
		flex: 1;
		overflow: hidden;
		background: rgba(212, 175, 55, 0.1);
	}

	.panel {
		display: flex;
		flex-direction: column;
		background: var(--bg-primary, #141412);
		overflow: hidden;
	}

	.panel-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.6rem 1rem;
		background: rgba(0, 0, 0, 0.3);
		border-bottom: 1px solid rgba(212, 175, 55, 0.15);
	}

	.version-label {
		font-family: 'Bebas Neue', sans-serif;
		font-size: 1rem;
		color: var(--noir-gold, #d4af37);
		letter-spacing: 0.1em;
	}

	.version-meta {
		font-family: 'Cormorant Garamond', serif;
		font-size: 0.8rem;
		color: var(--text-muted, #6a5d4d);
		font-style: italic;
	}

	.panel-content {
		flex: 1;
		overflow-y: auto;
		padding: 0.75rem;
	}

	.panel-content::-webkit-scrollbar {
		width: 6px;
	}

	.panel-content::-webkit-scrollbar-track {
		background: rgba(0, 0, 0, 0.2);
	}

	.panel-content::-webkit-scrollbar-thumb {
		background: var(--noir-gold-dim, #a68829);
		border-radius: 3px;
	}

	/* Items */
	.item {
		position: relative;
		padding: 0.75rem;
		margin-bottom: 0.5rem;
		border-radius: 4px;
		border-left: 3px solid transparent;
		transition: all 0.2s ease;
	}

	.item:last-child {
		margin-bottom: 0;
	}

	.item.unchanged {
		background: rgba(0, 0, 0, 0.2);
		border-left-color: rgba(100, 100, 100, 0.3);
	}

	.item.added {
		background: rgba(80, 200, 120, 0.08);
		border-left-color: #50c878;
	}

	.item.removed {
		background: rgba(196, 30, 58, 0.08);
		border-left-color: #c41e3a;
		opacity: 0.7;
	}

	.item.modified {
		background: rgba(212, 175, 55, 0.08);
		border-left-color: var(--noir-gold, #d4af37);
	}

	.item-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.4rem;
		gap: 0.5rem;
	}

	.item-category {
		font-family: 'Bebas Neue', sans-serif;
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--noir-gold-dim, #a68829);
		background: rgba(212, 175, 55, 0.1);
		padding: 0.15rem 0.4rem;
		border-radius: 2px;
		flex-shrink: 0;
	}

	.item-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	.item-score {
		font-family: 'Bebas Neue', sans-serif;
		font-size: 0.75rem;
		color: var(--text-secondary, #8a8070);
	}

	.score-change {
		margin-left: 0.35rem;
		font-weight: 600;
	}

	.score-change.positive {
		color: #50c878;
	}

	.score-change.negative {
		color: #f5a5b3;
	}

	.item-content {
		display: block;
		font-family: 'Cormorant Garamond', serif;
		font-size: 0.9rem;
		line-height: 1.45;
		color: var(--text-cream, #f5f0e6);
	}

	.change-indicator {
		font-family: 'Bebas Neue', sans-serif;
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		padding: 0.15rem 0.35rem;
		border-radius: 2px;
		flex-shrink: 0;
	}

	.item.added .change-indicator {
		background: rgba(80, 200, 120, 0.2);
		color: #50c878;
	}

	.item.removed .change-indicator {
		background: rgba(196, 30, 58, 0.2);
		color: #f5a5b3;
	}

	.item.modified .change-indicator {
		background: rgba(212, 175, 55, 0.2);
		color: var(--noir-gold, #d4af37);
	}

	/* Source citation */
	.source-citation {
		display: flex;
		align-items: flex-start;
		gap: 0.4rem;
		margin-top: 0.5rem;
		padding: 0.4rem 0.5rem;
		background: rgba(0, 0, 0, 0.25);
		border-radius: 3px;
		border-left: 2px solid rgba(212, 175, 55, 0.3);
	}

	.citation-icon {
		font-size: 0.75rem;
		flex-shrink: 0;
		line-height: 1.4;
	}

	.citation-text {
		font-family: 'Cormorant Garamond', serif;
		font-size: 0.8rem;
		font-style: italic;
		color: var(--text-muted, #6a5d4d);
		line-height: 1.4;
	}

	/* Single version view */
	.single-version .items-list {
		width: 100%;
		max-width: 500px;
		text-align: left;
	}

	/* Responsive */
	@media (max-width: 768px) {
		.modal {
			width: 95vw;
			max-height: 90vh;
		}

		.diff-panels {
			grid-template-columns: 1fr;
		}

		.panel.left {
			border-bottom: 1px solid rgba(212, 175, 55, 0.2);
			max-height: 40vh;
		}

		.version-selectors {
			flex-direction: column;
			gap: 0.75rem;
		}

		.arrow {
			transform: rotate(90deg);
		}
	}
</style>
