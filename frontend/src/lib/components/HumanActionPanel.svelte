<script lang="ts">
	import { humanTurnState, sendHumanVote, sendHumanNightAction } from '$lib/websocket';

	interface Props {
		seriesId: string;
		players: Array<{ name: string; is_alive: boolean }>;
	}

	let { seriesId, players }: Props = $props();

	function handleVote(target: string) {
		sendHumanVote(seriesId, target);
	}

	function handleNightAction(target: string) {
		sendHumanNightAction(seriesId, target);
	}

	function getRoleActionText(role: string | null): string {
		switch (role) {
			case 'mafia':
				return 'Choose who to eliminate';
			case 'doctor':
				return 'Choose who to protect';
			case 'deputy':
				return 'Choose who to investigate';
			default:
				return 'Choose your target';
		}
	}
</script>

{#if $humanTurnState.isMyTurn && ($humanTurnState.action === 'vote' || $humanTurnState.action === 'night_action')}
	<div class="action-panel" class:night={$humanTurnState.action === 'night_action'}>
		<div class="panel-header">
			{#if $humanTurnState.action === 'vote'}
				<h3>Cast Your Vote</h3>
				<p>Choose a player to vote for elimination, or skip.</p>
			{:else}
				<h3>{getRoleActionText($humanTurnState.role)}</h3>
				<p>This action is secret - only you can see it.</p>
			{/if}
		</div>

		<div class="targets">
			{#each $humanTurnState.validTargets as target}
				{@const player = players.find((p) => p.name === target)}
				<button
					class="target-btn"
					class:dead={player && !player.is_alive}
					onclick={() =>
						$humanTurnState.action === 'vote' ? handleVote(target) : handleNightAction(target)}
				>
					{target}
				</button>
			{/each}

			{#if $humanTurnState.action === 'vote'}
				<button class="target-btn skip" onclick={() => handleVote('no_lynch')}>
					Skip Vote (No Lynch)
				</button>
			{/if}
		</div>
	</div>
{/if}

<style>
	.action-panel {
		position: fixed;
		bottom: 2rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 1000;
		padding: 1.5rem;
		background: linear-gradient(135deg, rgba(26, 25, 23, 0.98) 0%, rgba(20, 20, 18, 0.98) 100%);
		border: 2px solid var(--accent);
		border-radius: 8px;
		box-shadow:
			0 10px 40px rgba(0, 0, 0, 0.5),
			0 0 20px rgba(212, 175, 55, 0.2);
		animation: slideUp 0.3s ease-out;
	}

	.action-panel.night {
		border-color: #6366f1;
		box-shadow:
			0 10px 40px rgba(0, 0, 0, 0.5),
			0 0 20px rgba(99, 102, 241, 0.3);
	}

	@keyframes slideUp {
		from {
			opacity: 0;
			transform: translateX(-50%) translateY(20px);
		}
		to {
			opacity: 1;
			transform: translateX(-50%) translateY(0);
		}
	}

	.panel-header {
		text-align: center;
		margin-bottom: 1rem;
	}

	.panel-header h3 {
		font-family: var(--font-display);
		font-size: 1.25rem;
		color: var(--accent);
		margin: 0 0 0.5rem 0;
	}

	.action-panel.night .panel-header h3 {
		color: #a5b4fc;
	}

	.panel-header p {
		font-family: var(--font-body);
		font-size: 0.85rem;
		color: var(--text-secondary);
		margin: 0;
	}

	.targets {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		justify-content: center;
		max-width: 500px;
	}

	.target-btn {
		padding: 0.6rem 1.2rem;
		background: var(--bg-primary);
		border: 1px solid var(--border-gold);
		border-radius: 4px;
		color: var(--text-cream);
		font-family: var(--font-body);
		font-size: 0.9rem;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.target-btn:hover {
		border-color: var(--accent);
		background: rgba(212, 175, 55, 0.1);
		transform: translateY(-2px);
	}

	.target-btn.skip {
		background: transparent;
		border-style: dashed;
		color: var(--text-muted);
	}

	.target-btn.skip:hover {
		color: var(--text-cream);
	}

	.target-btn.dead {
		opacity: 0.4;
		text-decoration: line-through;
	}
</style>
