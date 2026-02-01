<script lang="ts">
	import type { Cheatsheet } from '$lib/types';

	interface Props {
		cheatsheet: Cheatsheet | null;
		playerName: string;
		loading?: boolean;
		visible?: boolean;
		position?: 'above' | 'below';
	}

	let { cheatsheet, playerName, loading = false, visible = false, position = 'above' }: Props = $props();

	import type { CheatsheetItem } from '$lib/types';

	// Group items by category
	let groupedItems = $derived.by(() => {
		if (!cheatsheet?.items?.length) return new Map<string, CheatsheetItem[]>();
		const grouped = new Map<string, CheatsheetItem[]>();
		for (const item of cheatsheet.items) {
			const existing = grouped.get(item.category) || [];
			existing.push(item);
			grouped.set(item.category, existing);
		}
		return grouped;
	});

	// Category icons
	const categoryIcons: Record<string, string> = {
		strategy: '♟',
		behavior: '🎭',
		deception: '🃏',
		observation: '👁',
		voting: '🗳',
		communication: '💬',
		survival: '🛡',
		default: '📝'
	};

	function getIcon(category: string): string {
		return categoryIcons[category.toLowerCase()] || categoryIcons.default;
	}
</script>

{#if visible}
	<div class="cheatsheet-tooltip" class:loading class:below={position === 'below'}>
		<div class="tooltip-header">
			<span class="tooltip-title">{playerName}'s Playbook</span>
			{#if cheatsheet}
				<span class="version-badge">v{cheatsheet.version}</span>
			{/if}
		</div>

		<div class="tooltip-content">
			{#if loading}
				<div class="loading-state">
					<div class="loading-spinner"></div>
					<span>Loading strategies...</span>
				</div>
			{:else if !cheatsheet || !cheatsheet.items?.length}
				<div class="empty-state">
					<span class="empty-icon">📋</span>
					<span>No strategies learned yet</span>
				</div>
			{:else}
				{#each [...groupedItems.entries()] as [category, items]}
					<div class="category-section">
						<div class="category-header">
							<span class="category-icon">{getIcon(category)}</span>
							<span class="category-name">{category}</span>
						</div>
						<ul class="items-list">
							{#each items as item}
								<li class="cheatsheet-item">
									<span class="item-content">{item.content}</span>
									<div class="item-meta">
										<span class="helpfulness" title="Helpfulness score">
											{'★'.repeat(Math.min(5, Math.max(1, Math.round(item.helpfulness_score))))}
										</span>
									</div>
								</li>
							{/each}
						</ul>
					</div>
				{/each}
			{/if}
		</div>
	</div>
{/if}

<style>
	.cheatsheet-tooltip {
		position: absolute;
		bottom: 100%;
		left: 50%;
		transform: translateX(-50%);
		margin-bottom: 12px;
		width: 320px;
		max-height: 400px;
		background: var(--bg-card, linear-gradient(135deg, #1a1917 0%, #0f0e0d 100%));
		border: 1px solid var(--noir-gold-dim, #a68829);
		border-radius: 6px;
		box-shadow:
			0 8px 32px rgba(0, 0, 0, 0.6),
			0 0 20px var(--accent-glow, rgba(212, 175, 55, 0.1));
		z-index: 9999;
		overflow: hidden;
		animation: tooltipAppearAbove 0.2s ease-out;
		transition: background 0.4s ease, border-color 0.4s ease, box-shadow 0.4s ease;
	}

	/* Position below the player */
	.cheatsheet-tooltip.below {
		bottom: auto;
		top: 100%;
		margin-bottom: 0;
		margin-top: 12px;
		animation: tooltipAppearBelow 0.2s ease-out;
	}

	@keyframes tooltipAppearAbove {
		from {
			opacity: 0;
			transform: translateX(-50%) translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateX(-50%) translateY(0);
		}
	}

	@keyframes tooltipAppearBelow {
		from {
			opacity: 0;
			transform: translateX(-50%) translateY(-8px);
		}
		to {
			opacity: 1;
			transform: translateX(-50%) translateY(0);
		}
	}

	/* Arrow pointing down (for above position) */
	.cheatsheet-tooltip::after {
		content: '';
		position: absolute;
		bottom: -8px;
		left: 50%;
		transform: translateX(-50%);
		border-left: 8px solid transparent;
		border-right: 8px solid transparent;
		border-top: 8px solid var(--noir-gold-dim, #a68829);
	}

	/* Arrow pointing up (for below position) */
	.cheatsheet-tooltip.below::after {
		bottom: auto;
		top: -8px;
		border-top: none;
		border-bottom: 8px solid var(--noir-gold-dim, #a68829);
	}

	.tooltip-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		background: rgba(0, 0, 0, 0.3);
		border-bottom: 1px solid rgba(212, 175, 55, 0.2);
	}

	.tooltip-title {
		font-family: 'Playfair Display', serif;
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--noir-gold, #d4af37);
		letter-spacing: 0.02em;
	}

	.version-badge {
		font-family: 'Bebas Neue', sans-serif;
		font-size: 0.7rem;
		padding: 0.15rem 0.4rem;
		background: rgba(212, 175, 55, 0.15);
		border: 1px solid rgba(212, 175, 55, 0.3);
		border-radius: 3px;
		color: var(--noir-gold-dim, #a68829);
		letter-spacing: 0.05em;
	}

	.tooltip-content {
		padding: 0.75rem;
		max-height: 320px;
		overflow-y: auto;
	}

	/* Scrollbar styling */
	.tooltip-content::-webkit-scrollbar {
		width: 6px;
	}

	.tooltip-content::-webkit-scrollbar-track {
		background: rgba(0, 0, 0, 0.2);
	}

	.tooltip-content::-webkit-scrollbar-thumb {
		background: var(--noir-gold-dim, #a68829);
		border-radius: 3px;
	}

	/* Loading state */
	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
		padding: 2rem 1rem;
		color: var(--text-muted, #8a8070);
	}

	.loading-spinner {
		width: 24px;
		height: 24px;
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

	/* Empty state */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
		padding: 2rem 1rem;
		color: var(--text-muted, #6a5d4d);
		text-align: center;
	}

	.empty-icon {
		font-size: 1.5rem;
		opacity: 0.6;
	}

	/* Category sections */
	.category-section {
		margin-bottom: 0.75rem;
	}

	.category-section:last-child {
		margin-bottom: 0;
	}

	.category-header {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.35rem 0.5rem;
		background: rgba(212, 175, 55, 0.08);
		border-radius: 3px;
		margin-bottom: 0.4rem;
	}

	.category-icon {
		font-size: 0.8rem;
	}

	.category-name {
		font-family: 'Bebas Neue', sans-serif;
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--noir-gold-dim, #a68829);
	}

	.items-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.cheatsheet-item {
		padding: 0.5rem;
		margin-bottom: 0.35rem;
		background: var(--noir-smoke, rgba(0, 0, 0, 0.2));
		border-left: 2px solid var(--accent-glow, rgba(212, 175, 55, 0.3));
		border-radius: 0 3px 3px 0;
		transition: all 0.15s ease;
	}

	.cheatsheet-item:last-child {
		margin-bottom: 0;
	}

	.cheatsheet-item:hover {
		background: rgba(0, 0, 0, 0.35);
		border-left-color: var(--accent, #d4af37);
	}

	.item-content {
		display: block;
		font-family: 'Cormorant Garamond', serif;
		font-size: 0.85rem;
		line-height: 1.4;
		color: var(--text-secondary, #c9c0b0);
		transition: color 0.4s ease;
	}

	.item-meta {
		display: flex;
		justify-content: flex-end;
		margin-top: 0.25rem;
	}

	.helpfulness {
		font-size: 0.65rem;
		color: var(--noir-gold-dim, #a68829);
		letter-spacing: 0.05em;
	}

	/* Loading overlay effect */
	.cheatsheet-tooltip.loading .tooltip-content {
		opacity: 0.7;
	}
</style>
