<script lang="ts">
	import type { GamePhase } from '$lib/types';

	interface Props {
		currentPhase: GamePhase;
		dayNumber: number;
		alivePlayers: number;
		totalPlayers: number;
	}

	let { currentPhase, dayNumber, alivePlayers, totalPlayers }: Props = $props();

	const phases: { id: GamePhase; label: string; icon: string }[] = [
		{ id: 'pending', label: 'Setup', icon: '⏳' },
		{ id: 'day', label: 'Day', icon: '☀️' },
		{ id: 'voting', label: 'Vote', icon: '🗳️' },
		{ id: 'night', label: 'Night', icon: '🌙' },
		{ id: 'completed', label: 'End', icon: '🏆' }
	];

	function getPhaseIndex(phase: GamePhase): number {
		return phases.findIndex((p) => p.id === phase);
	}

	function isActive(phase: GamePhase): boolean {
		return currentPhase === phase;
	}

	function isPast(phase: GamePhase): boolean {
		if (currentPhase === 'completed') return true;
		const currentIdx = getPhaseIndex(currentPhase);
		const phaseIdx = getPhaseIndex(phase);
		// Day cycle: day -> voting -> night -> day...
		if (currentPhase === 'day') return phase === 'pending';
		if (currentPhase === 'voting') return phase === 'pending' || phase === 'day';
		if (currentPhase === 'night')
			return phase === 'pending' || phase === 'day' || phase === 'voting';
		return phaseIdx < currentIdx;
	}
</script>

<div class="state-diagram">
	<div class="header">
		<h3>Game State</h3>
		<div class="stats">
			<span class="stat">
				<span class="label">Day</span>
				<span class="value">{dayNumber}</span>
			</span>
			<span class="stat">
				<span class="label">Alive</span>
				<span class="value">{alivePlayers}/{totalPlayers}</span>
			</span>
		</div>
	</div>

	<div class="phases">
		{#each phases as phase, i}
			<div class="phase-wrapper">
				<div
					class="phase-node"
					class:active={isActive(phase.id)}
					class:past={isPast(phase.id)}
					class:pending={phase.id === 'pending'}
					class:day={phase.id === 'day'}
					class:voting={phase.id === 'voting'}
					class:night={phase.id === 'night'}
					class:completed={phase.id === 'completed'}
				>
					<span class="icon">{phase.icon}</span>
					<span class="label">{phase.label}</span>
				</div>
				{#if i < phases.length - 1}
					<div class="connector" class:active={isPast(phases[i + 1].id) || isActive(phases[i + 1].id)}>
						<svg viewBox="0 0 24 12" fill="none" xmlns="http://www.w3.org/2000/svg">
							<path d="M0 6H20M20 6L14 1M20 6L14 11" stroke="currentColor" stroke-width="2" />
						</svg>
					</div>
				{/if}
			</div>
		{/each}
	</div>

	<!-- Cycle indicator for day/night loop -->
	{#if currentPhase !== 'pending' && currentPhase !== 'completed'}
		<div class="cycle-indicator">
			<svg viewBox="0 0 100 30" fill="none" xmlns="http://www.w3.org/2000/svg">
				<path
					d="M85 15 C85 5, 50 5, 25 10 M25 10 L28 5 M25 10 L28 15"
					stroke="var(--text-muted)"
					stroke-width="1.5"
					fill="none"
					stroke-dasharray="4 2"
				/>
			</svg>
			<span class="cycle-label">Day/Night Cycle</span>
		</div>
	{/if}
</div>

<style>
	.state-diagram {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: 0.5rem;
		padding: 1rem;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1rem;
	}

	.header h3 {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--text-secondary);
		margin: 0;
	}

	.stats {
		display: flex;
		gap: 1rem;
	}

	.stat {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.125rem;
	}

	.stat .label {
		font-size: 0.625rem;
		color: var(--text-muted);
		text-transform: uppercase;
	}

	.stat .value {
		font-size: 0.875rem;
		font-weight: 600;
	}

	.phases {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0;
		overflow-x: auto;
		padding: 0.5rem 0;
	}

	.phase-wrapper {
		display: flex;
		align-items: center;
	}

	.phase-node {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.25rem;
		padding: 0.5rem 0.75rem;
		border-radius: 0.5rem;
		background: var(--bg-secondary);
		border: 2px solid var(--border);
		transition: all 0.3s ease;
		min-width: 60px;
	}

	.phase-node .icon {
		font-size: 1.25rem;
	}

	.phase-node .label {
		font-size: 0.6875rem;
		font-weight: 500;
		color: var(--text-secondary);
	}

	.phase-node.active {
		transform: scale(1.1);
		box-shadow: 0 0 20px rgba(233, 69, 96, 0.3);
	}

	.phase-node.active.day {
		border-color: #fbbf24;
		background: rgba(251, 191, 36, 0.1);
	}

	.phase-node.active.voting {
		border-color: #8b5cf6;
		background: rgba(139, 92, 246, 0.1);
	}

	.phase-node.active.night {
		border-color: #3b82f6;
		background: rgba(59, 130, 246, 0.1);
	}

	.phase-node.active.completed {
		border-color: #4ade80;
		background: rgba(74, 222, 128, 0.1);
	}

	.phase-node.past {
		opacity: 0.5;
	}

	.phase-node.past .icon {
		filter: grayscale(0.5);
	}

	.connector {
		width: 24px;
		height: 12px;
		color: var(--border);
		flex-shrink: 0;
	}

	.connector.active {
		color: var(--text-muted);
	}

	.connector svg {
		width: 100%;
		height: 100%;
	}

	.cycle-indicator {
		display: flex;
		flex-direction: column;
		align-items: center;
		margin-top: 0.5rem;
		position: relative;
	}

	.cycle-indicator svg {
		width: 100px;
		height: 30px;
	}

	.cycle-label {
		font-size: 0.625rem;
		color: var(--text-muted);
		margin-top: -0.25rem;
	}
</style>
