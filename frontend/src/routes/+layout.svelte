<script lang="ts">
	import '../app.css';

	let { children } = $props();
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
		background: linear-gradient(180deg, #141412 0%, #0a0908 100%);
		border-bottom: 1px solid var(--border-gold);
		padding: 1.25rem 2rem;
		position: relative;
		z-index: 100;
	}

	/* Subtle wood grain texture on header */
	header::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background:
			linear-gradient(90deg, transparent 0%, rgba(212, 175, 55, 0.02) 50%, transparent 100%);
		pointer-events: none;
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
	}
</style>
