<script lang="ts">
  interface Props {
    phase: string;  // 'day' | 'night' | 'voting' | 'setup' | 'ended'
    dayNumber: number;
  }

  let { phase, dayNumber }: Props = $props();

  // Map phase to display info
  const phaseInfo: Record<string, { icon: string; label: string; cssClass: string }> = {
    day: { icon: '☀️', label: 'Day', cssClass: 'day' },
    night: { icon: '🌙', label: 'Night', cssClass: 'night' },
    voting: { icon: '🗳️', label: 'Voting', cssClass: 'voting' },
    setup: { icon: '⚙️', label: 'Setup', cssClass: 'setup' },
    ended: { icon: '🏆', label: 'Game Over', cssClass: 'ended' }
  };

  let info = $derived(phaseInfo[phase] || phaseInfo.day);
</script>

<div class="phase-indicator {info.cssClass}">
  <span class="phase-icon">{info.icon}</span>
  <span class="phase-label">{info.label}</span>
  {#if phase !== 'setup' && phase !== 'ended'}
    <span class="day-badge">{dayNumber}</span>
  {/if}
</div>

<style>
  /* CSS Variables - Noir Palette */
  :root {
    --noir-charcoal: #141412;
    --noir-gold: #d4af37;
    --noir-gold-dim: #a68829;
    --noir-gold-bright: #f4cf47;

    --color-mafia: #c41e3a;

    --text-gold: #d4af37;
    --text-secondary: #a89880;

    /* Phase Gradients */
    --phase-night: linear-gradient(135deg, #0d1a2d 0%, #1a2744 50%, #0d1a2d 100%);
    --phase-discussion: linear-gradient(135deg, #2a2010 0%, #3d3020 50%, #2a2010 100%);
    --phase-voting: linear-gradient(135deg, #2d1515 0%, #4a2020 50%, #2d1515 100%);
    --phase-over: linear-gradient(135deg, #1a1510 0%, #2a2520 100%);
    --phase-setup: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 50%, #1a1a1a 100%);
  }

  /* Phase Indicator Container */
  .phase-indicator {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: 0.6rem 1rem;
    background: var(--noir-charcoal);
    border-radius: 4px;
    border: 2px solid var(--noir-gold-dim);
    min-width: 100px;
    transition: all 0.5s ease;
    box-shadow:
      0 0 15px rgba(0, 0, 0, 0.5),
      inset 0 1px 0 rgba(212, 175, 55, 0.1);
    position: relative;
  }

  /* Art Deco Diamond Accent */
  .phase-indicator::before {
    content: '';
    position: absolute;
    top: -5px;
    left: 50%;
    transform: translateX(-50%) rotate(45deg);
    width: 8px;
    height: 8px;
    background: var(--noir-gold);
    border: 1px solid var(--noir-gold-bright);
  }

  /* Phase-specific Styling */
  .phase-indicator.night {
    background: var(--phase-night);
    border-color: #4a6a9a;
    box-shadow:
      0 0 25px rgba(70, 100, 150, 0.3),
      inset 0 0 15px rgba(70, 100, 150, 0.1);
  }

  .phase-indicator.night::before {
    background: #4a6a9a;
    border-color: #6a8aba;
  }

  .phase-indicator.day {
    background: var(--phase-discussion);
    border-color: var(--noir-gold-dim);
    box-shadow:
      0 0 25px rgba(212, 175, 55, 0.2),
      inset 0 0 15px rgba(212, 175, 55, 0.05);
  }

  .phase-indicator.voting {
    background: var(--phase-voting);
    border-color: var(--color-mafia);
    box-shadow:
      0 0 25px rgba(196, 30, 58, 0.3),
      inset 0 0 15px rgba(196, 30, 58, 0.1);
  }

  .phase-indicator.voting::before {
    background: var(--color-mafia);
    border-color: #e4304a;
  }

  .phase-indicator.setup {
    background: var(--phase-setup);
    border-color: var(--noir-gold-dim);
    box-shadow:
      0 0 15px rgba(0, 0, 0, 0.5),
      inset 0 1px 0 rgba(212, 175, 55, 0.1);
    animation: loadingPulse 2s ease-in-out infinite;
  }

  @keyframes loadingPulse {
    0%, 100% {
      box-shadow: 0 0 15px rgba(212, 175, 55, 0.2);
    }
    50% {
      box-shadow: 0 0 30px rgba(212, 175, 55, 0.4);
    }
  }

  .phase-indicator.ended {
    background: var(--phase-over);
    border-color: var(--noir-gold);
    box-shadow:
      0 0 35px rgba(212, 175, 55, 0.4),
      inset 0 0 25px rgba(212, 175, 55, 0.1);
  }

  .phase-indicator.ended::before {
    background: var(--noir-gold-bright);
    border-color: var(--noir-gold-bright);
  }

  /* Phase Icon */
  .phase-icon {
    font-size: 1.5rem;
    margin-bottom: 0.15rem;
    filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.5));
  }

  /* Phase Label */
  .phase-label {
    font-family: 'Bebas Neue', sans-serif;
    font-weight: 400;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-gold);
  }

  /* Day Number Badge */
  .day-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 0.25rem;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--noir-gold-dim) 0%, var(--noir-gold) 100%);
    border: 1px solid var(--noir-gold-bright);
    font-family: 'Cormorant Garamond', serif;
    font-size: 0.75rem;
    font-weight: 700;
    color: #0a0908;
    box-shadow:
      0 2px 4px rgba(0, 0, 0, 0.3),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);
  }

  /* Night phase badge adjustment */
  .phase-indicator.night .day-badge {
    background: linear-gradient(135deg, #3a5a8a 0%, #4a6a9a 100%);
    border-color: #6a8aba;
    color: #f5e6c8;
  }

  /* Voting phase badge adjustment */
  .phase-indicator.voting .day-badge {
    background: linear-gradient(135deg, #a41e3a 0%, var(--color-mafia) 100%);
    border-color: #e4304a;
    color: #f5e6c8;
  }
</style>
