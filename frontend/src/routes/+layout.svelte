<script lang="ts">
	import '../app.css';
	import { browser } from '$app/environment';
	import { audioEnabled, setAudioEnabled } from '$lib/websocket';

	let { children } = $props();

	// Theme state - persisted to localStorage
	let isLightTheme = $state(false);

	// Audio state - synced with store and localStorage
	let isAudioEnabled = $state(false);

	// Initialize theme from localStorage on mount
	$effect(() => {
		if (browser) {
			const savedTheme = localStorage.getItem('mafia-ace-theme');
			const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

			if (savedTheme === 'light') {
				isLightTheme = true;
			} else if (savedTheme === 'dark') {
				isLightTheme = false;
			} else {
				// No preference saved, use system preference (dark by default for this app)
				isLightTheme = !prefersDark;
			}

			// Initialize audio preference from localStorage
			const savedAudio = localStorage.getItem('mafia-ace-audio');
			if (savedAudio === 'true') {
				isAudioEnabled = true;
				setAudioEnabled(true);
			}
		}
	});

	// Sync with store changes
	$effect(() => {
		const unsubscribe = audioEnabled.subscribe((value) => {
			isAudioEnabled = value;
		});
		return unsubscribe;
	});

	// Apply theme class to document root
	$effect(() => {
		if (browser) {
			if (isLightTheme) {
				document.documentElement.classList.add('light-theme');
			} else {
				document.documentElement.classList.remove('light-theme');
			}
		}
	});

	function toggleTheme() {
		isLightTheme = !isLightTheme;
		if (browser) {
			localStorage.setItem('mafia-ace-theme', isLightTheme ? 'light' : 'dark');
		}
	}

	function toggleAudio() {
		isAudioEnabled = !isAudioEnabled;
		setAudioEnabled(isAudioEnabled);
		if (browser) {
			localStorage.setItem('mafia-ace-audio', isAudioEnabled ? 'true' : 'false');
		}
	}
</script>

<svelte:head>
	<title>Mafia ACE - Agents Learning the Metagame of Mafia</title>
</svelte:head>

<div class="app">
	<header>
		<nav>
			<a href="/" class="logo">
				<span class="logo-icon">
					<!-- Art Deco Diamond -->
					<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
						<path d="M12 2L22 12L12 22L2 12L12 2Z" fill="currentColor" opacity="0.2"/>
						<path d="M12 2L22 12L12 22L2 12L12 2Z" stroke="currentColor" stroke-width="1.5"/>
						<circle cx="12" cy="12" r="3" fill="currentColor"/>
					</svg>
				</span>
				<span class="logo-text">
					<span class="logo-main">Mafia</span>
					<span class="logo-accent">ACE</span>
				</span>
			</a>
			<div class="tagline-wrapper">
				<span class="tagline-diamond"></span>
				<span class="tagline">Agents Learning the Metagame of Mafia</span>
				<span class="tagline-diamond"></span>
			</div>
			<div class="header-controls">
				<button
					class="audio-toggle"
					onclick={toggleAudio}
					aria-label={isAudioEnabled ? 'Disable audio' : 'Enable audio'}
					title={isAudioEnabled ? 'Disable audio' : 'Enable audio'}
				>
					<span class="toggle-track">
						<span class="toggle-thumb" class:enabled={isAudioEnabled}>
							{#if isAudioEnabled}
								<!-- Speaker on icon -->
								<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
									<path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
									<path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
								</svg>
							{:else}
								<!-- Speaker off icon -->
								<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
									<line x1="23" y1="9" x2="17" y2="15"/>
									<line x1="17" y1="9" x2="23" y2="15"/>
								</svg>
							{/if}
						</span>
					</span>
				</button>
				<button
					class="theme-toggle"
					onclick={toggleTheme}
					aria-label={isLightTheme ? 'Switch to dark theme' : 'Switch to light theme'}
					title={isLightTheme ? 'Switch to dark theme' : 'Switch to light theme'}
				>
					<span class="toggle-track">
						<span class="toggle-thumb" class:light={isLightTheme}>
							{#if isLightTheme}
								<!-- Sun icon -->
								<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<circle cx="12" cy="12" r="5"/>
									<path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
								</svg>
							{:else}
								<!-- Moon icon -->
								<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
									<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
								</svg>
							{/if}
						</span>
					</span>
				</button>
			</div>
		</nav>
	</header>

	<main>
		{@render children()}
	</main>

	<footer>
		<div class="footer-content">
			<div class="footer-decoration"></div>
			<span class="footer-text">The House Always Watches</span>
			<div class="footer-decoration"></div>
		</div>
	</footer>
</div>

<style>
	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
		position: relative;
	}

	/* ============================================
	   HEADER - Speakeasy Bar Style
	   ============================================ */
	header {
		background: var(--header-gradient);
		border-bottom: 1px solid var(--border-gold);
		padding: 1.25rem 2rem;
		position: relative;
		z-index: 100;
		transition: background 0.4s ease, border-color 0.4s ease;
	}

	/* Subtle sheen texture on header */
	header::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: var(--header-sheen);
		pointer-events: none;
		transition: background 0.4s ease;
	}

	/* Gold accent line at bottom */
	header::after {
		content: '';
		position: absolute;
		bottom: 0;
		left: 50%;
		transform: translateX(-50%);
		width: 200px;
		height: 2px;
		background: linear-gradient(90deg, transparent, var(--accent-dim), transparent);
	}

	nav {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 2rem;
		max-width: 1400px;
		margin: 0 auto;
		position: relative;
	}

	/* ============================================
	   LOGO - Art Deco Typography
	   ============================================ */
	.logo {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		text-decoration: none;
		color: inherit;
		transition: all 0.3s ease;
	}

	.logo:hover {
		transform: translateY(-1px);
	}

	.logo:hover .logo-icon {
		filter: drop-shadow(0 0 8px rgba(212, 175, 55, 0.5));
	}

	.logo-icon {
		width: 32px;
		height: 32px;
		color: var(--accent);
		transition: filter 0.3s ease;
	}

	.logo-icon svg {
		width: 100%;
		height: 100%;
	}

	.logo-text {
		display: flex;
		flex-direction: column;
		line-height: 1;
	}

	.logo-main {
		font-family: var(--font-display);
		font-size: 1.75rem;
		font-weight: 700;
		letter-spacing: 0.05em;
		background: linear-gradient(135deg, var(--text-cream) 0%, var(--accent) 100%);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.logo-accent {
		font-family: var(--font-heading);
		font-size: 0.9rem;
		font-weight: 400;
		letter-spacing: 0.4em;
		color: var(--accent-dim);
		margin-top: 2px;
	}

	/* ============================================
	   TAGLINE - Vintage Subtitle
	   ============================================ */
	.tagline-wrapper {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.tagline-diamond {
		width: 6px;
		height: 6px;
		background: var(--accent-dim);
		transform: rotate(45deg);
		opacity: 0.6;
	}

	.tagline {
		font-family: var(--font-body);
		font-size: 1rem;
		font-style: italic;
		color: var(--text-secondary);
		letter-spacing: 0.05em;
	}

	/* ============================================
	   MAIN CONTENT
	   ============================================ */
	main {
		flex: 1;
		padding: 2.5rem;
		max-width: 1400px;
		margin: 0 auto;
		width: 100%;
		position: relative;
		z-index: 1;
	}

	/* ============================================
	   FOOTER - Subtle Branding
	   ============================================ */
	footer {
		padding: 1.5rem 2rem;
		border-top: 1px solid var(--border);
		background: var(--bg-primary);
		position: relative;
	}

	.footer-content {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1.5rem;
		max-width: 1400px;
		margin: 0 auto;
	}

	.footer-decoration {
		width: 60px;
		height: 1px;
		background: linear-gradient(90deg, transparent, var(--border-gold), transparent);
	}

	.footer-text {
		font-family: var(--font-heading);
		font-size: 0.7rem;
		letter-spacing: 0.25em;
		text-transform: uppercase;
		color: var(--text-muted);
	}

	/* ============================================
	   HEADER CONTROLS - Toggle Buttons Container
	   ============================================ */
	.header-controls {
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	/* ============================================
	   TOGGLE BUTTONS - Art Deco Switch (shared)
	   ============================================ */
	.theme-toggle,
	.audio-toggle {
		all: unset;
		cursor: pointer;
		padding: 0;
		margin: 0;
		display: flex;
		align-items: center;
	}

	.toggle-track {
		display: flex;
		align-items: center;
		justify-content: flex-start;
		width: 52px;
		height: 28px;
		background: var(--bg-primary);
		border: 1px solid var(--border-gold);
		border-radius: 14px;
		padding: 2px;
		transition: all 0.3s ease;
		position: relative;
		box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2);
	}

	.theme-toggle:hover .toggle-track {
		border-color: var(--accent);
		box-shadow:
			inset 0 2px 4px rgba(0, 0, 0, 0.2),
			0 0 12px var(--accent-glow);
	}

	.toggle-thumb {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dim) 100%);
		border-radius: 50%;
		transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
		box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
		transform: translateX(0);
	}

	.toggle-thumb.light {
		transform: translateX(24px);
	}

	.toggle-thumb svg {
		width: 12px;
		height: 12px;
		color: var(--bg-primary);
		transition: transform 0.3s ease;
	}

	.theme-toggle:hover .toggle-thumb svg {
		transform: rotate(15deg);
	}

	.toggle-thumb.light svg {
		color: var(--button-text);
	}

	/* Audio toggle enabled state */
	.toggle-thumb.enabled {
		transform: translateX(24px);
	}

	.toggle-thumb.enabled svg {
		color: var(--button-text);
	}

	.audio-toggle:hover .toggle-track {
		border-color: var(--accent);
		box-shadow:
			inset 0 2px 4px rgba(0, 0, 0, 0.2),
			0 0 12px var(--accent-glow);
	}

	/* ============================================
	   RESPONSIVE
	   ============================================ */
	@media (max-width: 768px) {
		header {
			padding: 1rem;
		}

		nav {
			flex-direction: column;
			gap: 1rem;
		}

		.tagline-wrapper {
			display: none;
		}

		main {
			padding: 1.5rem;
		}

		.logo-main {
			font-size: 1.5rem;
		}

		.logo-accent {
			font-size: 0.75rem;
		}

		.header-controls {
			position: absolute;
			top: 1rem;
			right: 1rem;
		}
	}
</style>
