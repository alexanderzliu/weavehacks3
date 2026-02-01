<script lang="ts">
	import { humanTurnState, sendHumanVote, sendHumanNightAction, sendHumanSpeech } from '$lib/websocket';

	interface Props {
		seriesId: string;
		players: Array<{ name: string; is_alive: boolean }>;
	}

	let { seriesId, players }: Props = $props();

	// Speech input state
	let speechText = $state('');

	function handleVote(target: string) {
		sendHumanVote(seriesId, target);
	}

	function handleNightAction(target: string) {
		sendHumanNightAction(seriesId, target);
	}

	function handleSpeech() {
		if (speechText.trim()) {
			sendHumanSpeech(seriesId, speechText.trim());
			speechText = '';
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSpeech();
		}
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

{#if $humanTurnState.isMyTurn}
	<div class="action-panel" class:night={$humanTurnState.action === 'night_action'} class:speech={$humanTurnState.action === 'speech'}>
		<div class="panel-header">
			{#if $humanTurnState.action === 'speech'}
				<h3>Your Turn to Speak</h3>
				<p>Share your thoughts with the group. Press Enter to send.</p>
			{:else if $humanTurnState.action === 'vote'}
				<h3>Cast Your Vote</h3>
				<p>Choose a player to vote for elimination, or skip.</p>
			{:else}
				<h3>{getRoleActionText($humanTurnState.role)}</h3>
				<p>This action is secret - only you can see it.</p>
			{/if}
		</div>

		{#if $humanTurnState.action === 'speech'}
			<div class="speech-input">
				<textarea
					bind:value={speechText}
					placeholder="What would you like to say?"
					rows="3"
					onkeydown={handleKeydown}
				></textarea>
				<button class="send-btn" onclick={handleSpeech} disabled={!speechText.trim()}>
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<line x1="22" y1="2" x2="11" y2="13"/>
						<polygon points="22 2 15 22 11 13 2 9 22 2"/>
					</svg>
					Send
				</button>
			</div>
		{:else}
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
		{/if}
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

	/* Speech input styles */
	.action-panel.speech {
		border-color: var(--success);
		box-shadow:
			0 10px 40px rgba(0, 0, 0, 0.5),
			0 0 20px rgba(80, 200, 120, 0.2);
	}

	.action-panel.speech .panel-header h3 {
		color: var(--success);
	}

	.speech-input {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		min-width: 400px;
	}

	.speech-input textarea {
		width: 100%;
		padding: 0.75rem;
		background: var(--bg-primary);
		border: 1px solid var(--border-gold);
		border-radius: 4px;
		color: var(--text-cream);
		font-family: var(--font-body);
		font-size: 0.95rem;
		line-height: 1.5;
		resize: vertical;
		min-height: 80px;
	}

	.speech-input textarea:focus {
		outline: none;
		border-color: var(--success);
		box-shadow: 0 0 10px rgba(80, 200, 120, 0.2);
	}

	.speech-input textarea::placeholder {
		color: var(--text-muted);
	}

	.send-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		padding: 0.75rem 1.5rem;
		background: var(--success);
		border: none;
		border-radius: 4px;
		color: var(--bg-primary);
		font-family: var(--font-heading);
		font-size: 0.85rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		cursor: pointer;
		transition: all 0.2s ease;
		align-self: flex-end;
	}

	.send-btn:hover:not(:disabled) {
		background: #5dd97a;
		transform: translateY(-2px);
	}

	.send-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.send-btn svg {
		width: 16px;
		height: 16px;
	}
</style>
