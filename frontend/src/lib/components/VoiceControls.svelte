<script lang="ts">
	import { voiceState, toggleMute, connectVoice, disconnectVoice, setMuted } from '$lib/voice';

	interface Props {
		roomUrl: string | null;
		roomToken: string | null;
		playerName: string;
		isHumanTurn?: boolean;
	}

	let { roomUrl, roomToken, playerName, isHumanTurn = false }: Props = $props();

	let isConnecting = $state(false);
	let previousTurnState = $state(false);

	// Auto-unmute when it becomes human's turn, auto-mute when turn ends
	$effect(() => {
		if (isHumanTurn && !previousTurnState && $voiceState.connectionState === 'connected') {
			// Turn just started - unmute
			setMuted(false);
		} else if (!isHumanTurn && previousTurnState && $voiceState.connectionState === 'connected') {
			// Turn just ended - mute
			setMuted(true);
		}
		previousTurnState = isHumanTurn;
	});

	async function handleConnect() {
		if (!roomUrl || !roomToken) return;

		isConnecting = true;
		try {
			await connectVoice(roomUrl, roomToken);
			// Start muted - will unmute when it's our turn
			setMuted(true);
		} finally {
			isConnecting = false;
		}
	}

	async function handleDisconnect() {
		await disconnectVoice();
	}

	function handleToggleMute() {
		toggleMute();
	}
</script>

<div class="voice-controls" class:active={isHumanTurn}>
	{#if $voiceState.connectionState === 'disconnected'}
		<button class="connect-btn" onclick={handleConnect} disabled={isConnecting || !roomUrl}>
			{#if isConnecting}
				<span class="spinner"></span>
				Connecting...
			{:else}
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
					<path d="M19 10v2a7 7 0 0 1-14 0v-2" />
					<line x1="12" y1="19" x2="12" y2="23" />
					<line x1="8" y1="23" x2="16" y2="23" />
				</svg>
				Join Voice Chat
			{/if}
		</button>
	{:else if $voiceState.connectionState === 'connecting'}
		<div class="status connecting">
			<span class="spinner"></span>
			<span>Connecting voice...</span>
		</div>
	{:else if $voiceState.connectionState === 'connected'}
		<div class="connected-controls">
			{#if isHumanTurn}
				<div class="speak-now-indicator">
					<div class="mic-icon-animated">
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
							<path d="M19 10v2a7 7 0 0 1-14 0v-2" />
							<line x1="12" y1="19" x2="12" y2="23" />
							<line x1="8" y1="23" x2="16" y2="23" />
						</svg>
					</div>
					<span class="speak-now-text">SPEAK NOW</span>
				</div>
			{:else}
				<div class="status-indicator">
					<span class="pulse-dot" class:muted={$voiceState.isMuted}></span>
					<span class="status-text">
						{#if $voiceState.isMuted}
							Waiting for your turn...
						{:else}
							{playerName} (You)
						{/if}
					</span>
				</div>
			{/if}

			<div class="control-buttons">
				<button
					class="mute-btn"
					class:muted={$voiceState.isMuted}
					onclick={handleToggleMute}
					title={$voiceState.isMuted ? 'Unmute' : 'Mute'}
					disabled={isHumanTurn}
				>
					{#if $voiceState.isMuted}
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<line x1="1" y1="1" x2="23" y2="23" />
							<path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
							<path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2a7 7 0 0 1-.11 1.23" />
							<line x1="12" y1="19" x2="12" y2="23" />
							<line x1="8" y1="23" x2="16" y2="23" />
						</svg>
					{:else}
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
							<path d="M19 10v2a7 7 0 0 1-14 0v-2" />
							<line x1="12" y1="19" x2="12" y2="23" />
							<line x1="8" y1="23" x2="16" y2="23" />
						</svg>
					{/if}
				</button>

				<button class="disconnect-btn" onclick={handleDisconnect} title="Leave voice chat">
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path
							d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.63A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91"
						/>
						<line x1="23" y1="1" x2="1" y2="23" />
					</svg>
				</button>
			</div>
		</div>
	{:else if $voiceState.connectionState === 'error'}
		<div class="status error">
			<span class="error-icon">!</span>
			<span>{$voiceState.error || 'Connection failed'}</span>
			<button class="retry-btn" onclick={handleConnect}>Retry</button>
		</div>
	{/if}
</div>

<style>
	.voice-controls {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.5rem 0.75rem;
		background: var(--bg-secondary);
		border: 1px solid var(--border);
		border-radius: 4px;
		transition: all 0.3s ease;
	}

	.voice-controls.active {
		border-color: var(--success);
		background: rgba(80, 200, 120, 0.1);
		box-shadow: 0 0 10px rgba(80, 200, 120, 0.2);
	}

	.connect-btn {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 1rem;
		background: var(--accent);
		color: var(--bg-primary);
		border: none;
		border-radius: 4px;
		font-family: var(--font-heading);
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.connect-btn:hover:not(:disabled) {
		background: var(--accent-bright);
	}

	.connect-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.connect-btn svg {
		width: 16px;
		height: 16px;
	}

	.connected-controls {
		display: flex;
		align-items: center;
		gap: 1rem;
		width: 100%;
	}

	.status-indicator {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex: 1;
	}

	.status-indicator.speaking {
		animation: speakingPulse 1s ease-in-out infinite;
	}

	@keyframes speakingPulse {
		0%,
		100% {
			opacity: 1;
		}
		50% {
			opacity: 0.7;
		}
	}

	.pulse-dot {
		width: 10px;
		height: 10px;
		background: var(--success);
		border-radius: 50%;
		animation: pulse 2s ease-in-out infinite;
	}

	.pulse-dot.muted {
		background: var(--text-muted);
		animation: none;
	}

	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
			transform: scale(1);
		}
		50% {
			opacity: 0.6;
			transform: scale(0.9);
		}
	}

	.status-text {
		font-family: var(--font-body);
		font-size: 0.85rem;
		color: var(--text-secondary);
	}

	.status-indicator.speaking .status-text {
		color: var(--success);
		font-weight: 500;
	}

	.control-buttons {
		display: flex;
		gap: 0.5rem;
	}

	.mute-btn,
	.disconnect-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		background: var(--bg-primary);
		border: 1px solid var(--border);
		border-radius: 50%;
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.2s ease;
	}

	.mute-btn:hover,
	.disconnect-btn:hover {
		border-color: var(--accent-dim);
		color: var(--text-cream);
	}

	.mute-btn.muted {
		background: rgba(196, 30, 58, 0.2);
		border-color: var(--danger);
		color: var(--danger);
	}

	.disconnect-btn:hover {
		background: rgba(196, 30, 58, 0.2);
		border-color: var(--danger);
		color: var(--danger);
	}

	.mute-btn svg,
	.disconnect-btn svg {
		width: 18px;
		height: 18px;
	}

	.status {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.85rem;
	}

	.status.connecting {
		color: var(--accent);
	}

	.status.error {
		color: var(--danger);
	}

	.spinner {
		width: 14px;
		height: 14px;
		border: 2px solid currentColor;
		border-top-color: transparent;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
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
		width: 18px;
		height: 18px;
		background: var(--danger);
		color: white;
		border-radius: 50%;
		font-size: 0.7rem;
		font-weight: bold;
	}

	.retry-btn {
		padding: 0.25rem 0.5rem;
		background: transparent;
		border: 1px solid var(--danger);
		border-radius: 4px;
		color: var(--danger);
		font-size: 0.75rem;
		cursor: pointer;
	}

	.retry-btn:hover {
		background: rgba(196, 30, 58, 0.1);
	}

	/* Speak Now indicator */
	.speak-now-indicator {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex: 1;
		padding: 0.5rem 1rem;
		background: rgba(80, 200, 120, 0.15);
		border: 2px solid var(--success);
		border-radius: 8px;
		animation: speakNowPulse 1.5s ease-in-out infinite;
	}

	@keyframes speakNowPulse {
		0%, 100% {
			box-shadow: 0 0 10px rgba(80, 200, 120, 0.3);
		}
		50% {
			box-shadow: 0 0 20px rgba(80, 200, 120, 0.6);
		}
	}

	.mic-icon-animated {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		color: var(--success);
		animation: micPulse 1s ease-in-out infinite;
	}

	.mic-icon-animated svg {
		width: 24px;
		height: 24px;
	}

	@keyframes micPulse {
		0%, 100% {
			transform: scale(1);
		}
		50% {
			transform: scale(1.1);
		}
	}

	.speak-now-text {
		font-family: var(--font-heading);
		font-size: 1rem;
		font-weight: 600;
		color: var(--success);
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}

	.mute-btn:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}
</style>
