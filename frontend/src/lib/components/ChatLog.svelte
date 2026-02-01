<script lang="ts">
	import type { GameEvent } from '$lib/types';

	interface Props {
		events: GameEvent[];
	}

	let { events }: Props = $props();

	// Auto-scroll to bottom
	let chatContainer: HTMLDivElement;

	$effect(() => {
		if (chatContainer && events.length > 0) {
			chatContainer.scrollTop = chatContainer.scrollHeight;
		}
	});

	// Format event for display
	function formatEvent(event: GameEvent): { icon: string; text: string; type: string } {
		const p = event.payload as Record<string, unknown>;

		switch (event.type) {
			case 'speech':
				return {
					icon: '💬',
					text: `${p.player_name || 'Player'}: "${p.content}"`,
					type: 'speech'
				};
			case 'vote_cast':
				return {
					icon: '🗳️',
					text: `${p.voter_name || 'Player'} voted for ${p.target_name || 'someone'}`,
					type: 'vote'
				};
			case 'lynch_result':
				return {
					icon: '⚖️',
					text: p.lynched_player_name
						? `${p.lynched_player_name} was lynched! (${p.role})`
						: 'No one was lynched.',
					type: 'death'
				};
			case 'night_result':
				return {
					icon: '🌙',
					text: p.killed_player_name
						? `${p.killed_player_name} was found dead!`
						: 'Everyone survived the night.',
					type: p.killed_player_name ? 'death' : 'system'
				};
			case 'day_started':
				return { icon: '☀️', text: `Day ${p.day_number} begins`, type: 'system' };
			case 'night_started':
				return { icon: '🌑', text: `Night ${p.day_number} falls`, type: 'system' };
			case 'game_started':
				return { icon: '🎮', text: 'Game started!', type: 'system' };
			case 'game_ended':
				return {
					icon: '🏆',
					text: `Game over! ${p.winner === 'mafia' ? 'Mafia wins!' : 'Town wins!'}`,
					type: 'system'
				};
			default:
				return { icon: '📌', text: event.type, type: 'system' };
		}
	}
</script>

<div class="chat-log-section">
	<div class="chat-log" bind:this={chatContainer}>
		{#each events as event (event.id)}
			{@const formatted = formatEvent(event)}
			<div class="chat-message {formatted.type}">
				<span class="message-icon">{formatted.icon}</span>
				<span class="message-text">{formatted.text}</span>
			</div>
		{/each}
	</div>
</div>

<style>
	/* Chat Log Section - Expanded Panel */
	.chat-log-section {
		flex: 1;
		min-height: 250px;
		background: linear-gradient(180deg, var(--noir-dark, #1a1917) 0%, var(--noir-charcoal, #141412) 100%);
		border-radius: 4px;
		border: 1px solid var(--border-gold, #8b7355);
		display: flex;
		flex-direction: column;
		overflow: hidden;
		box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.3);
	}

	/* Scrollable Chat Container */
	.chat-log {
		flex: 1;
		overflow-y: auto;
		padding: 0.5rem 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	/* Chat Message - Compact inline format */
	.chat-message {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		padding: 0.3rem 0.5rem;
		background: rgba(0, 0, 0, 0.2);
		border-radius: 3px;
		font-size: 0.8rem;
		line-height: 1.4;
		animation: messageSlideIn 0.25s ease-out;
	}

	@keyframes messageSlideIn {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.message-icon {
		font-size: 0.9rem;
		flex-shrink: 0;
		width: 1.1rem;
		text-align: center;
	}

	.message-text {
		color: var(--text-secondary, #a89880);
		flex: 1;
		min-width: 0;
		word-break: break-word;
	}

	/* Message Type-Specific Styling */
	.chat-message.speech {
		border-left: 2px solid var(--noir-gold, #d4af37);
	}

	.chat-message.speech .message-text {
		color: var(--text-primary, #f5e6c8);
	}

	.chat-message.vote {
		border-left: 2px solid var(--color-detective, #6b3fa0);
	}

	.chat-message.vote .message-text {
		color: var(--color-detective, #6b3fa0);
	}

	.chat-message.death {
		border-left: 2px solid var(--color-mafia, #c41e3a);
		background: rgba(196, 30, 58, 0.1);
	}

	.chat-message.death .message-text {
		color: var(--color-mafia, #c41e3a);
		font-weight: 600;
	}

	.chat-message.system {
		border-left: 2px solid var(--text-gold, #d4af37);
		font-style: italic;
	}

	.chat-message.system .message-text {
		color: var(--text-gold, #d4af37);
	}

	/* Scrollbar Styling - Noir Theme */
	.chat-log::-webkit-scrollbar {
		width: 6px;
	}

	.chat-log::-webkit-scrollbar-track {
		background: var(--noir-black, #0a0908);
	}

	.chat-log::-webkit-scrollbar-thumb {
		background: var(--noir-gold-dim, #a68829);
		border-radius: 3px;
	}

	.chat-log::-webkit-scrollbar-thumb:hover {
		background: var(--noir-gold, #d4af37);
	}

	/* Firefox Scrollbar */
	.chat-log {
		scrollbar-width: thin;
		scrollbar-color: var(--noir-gold-dim, #a68829) var(--noir-black, #0a0908);
	}
</style>
