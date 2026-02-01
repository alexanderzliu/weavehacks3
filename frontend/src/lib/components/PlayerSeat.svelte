<script lang="ts">
  import CheatsheetTooltip from './CheatsheetTooltip.svelte';
  import type { Cheatsheet } from '$lib/types';

  interface Props {
    name: string;
    playerId?: string;
    role: string;  // 'mafia' | 'doctor' | 'deputy' | 'townsperson'
    isAlive: boolean;
    isSpeaking: boolean;
    position: { x: number; y: number };
    tableCenter?: { x: number; y: number };
    cheatsheet?: Cheatsheet | null;
    cheatsheetLoading?: boolean;
    onHover?: (playerId: string | null) => void;
    scaleFactor?: number;
  }

  let { name, playerId, role, isAlive, isSpeaking, position, tableCenter, cheatsheet = null, cheatsheetLoading = false, onHover, scaleFactor = 1 }: Props = $props();

  // Determine tooltip position: show below for top-half players (to avoid header), above for bottom-half
  let tooltipPosition = $derived.by((): 'above' | 'below' => {
    if (!tableCenter) return 'below';
    return position.y < tableCenter.y ? 'below' : 'above';
  });

  let isHovered = $state(false);

  function handleMouseEnter() {
    isHovered = true;
    if (playerId && onHover) {
      onHover(playerId);
    }
  }

  function handleMouseLeave() {
    isHovered = false;
    if (onHover) {
      onHover(null);
    }
  }

  // Map role to display name and CSS class
  const roleMap: Record<string, { display: string; cssClass: string }> = {
    mafia: { display: 'Mafia', cssClass: 'mafia' },
    doctor: { display: 'Doctor', cssClass: 'doctor' },
    deputy: { display: 'Detective', cssClass: 'detective' },
    townsperson: { display: 'Villager', cssClass: 'villager' }
  };

  // Role emoji
  const roleEmoji: Record<string, string> = {
    mafia: '🔪',
    doctor: '💊',
    deputy: '🔍',
    townsperson: '👤'
  };

  // Derived values
  const roleInfo = $derived(roleMap[role] || { display: 'Unknown', cssClass: 'villager' });
  const emoji = $derived(roleEmoji[role] || '👤');
</script>

<div
  class="player-seat {roleInfo.cssClass}"
  class:dead={!isAlive}
  class:speaking={isSpeaking}
  class:hovered={isHovered}
  style="left: {position.x}px; top: {position.y}px; --scale: {scaleFactor};"
  onmouseenter={handleMouseEnter}
  onmouseleave={handleMouseLeave}
  role="button"
  tabindex="0"
>
  <CheatsheetTooltip
    {cheatsheet}
    playerName={name}
    loading={cheatsheetLoading}
    visible={isHovered && playerId !== undefined}
    position={tooltipPosition}
  />

  <div class="player-avatar-container">
    <div class="player-avatar">
      <span class="avatar-emoji">{emoji}</span>
    </div>
    {#if isAlive}
      <div class="status-indicator alive"></div>
    {/if}
  </div>

  <div class="player-name-tag">{name}</div>

  <div class="player-role-tag">{roleInfo.display}</div>
</div>

<style>
  /* CSS Variables - Noir Palette */
  :root {
    --noir-charcoal: #141412;
    --noir-gold: #d4af37;
    --noir-gold-dim: #a68829;
    --noir-gold-bright: #f4cf47;
    --noir-burgundy-deep: #4a1f24;
    --noir-black: #0a0908;

    --color-mafia: #c41e3a;
    --color-mafia-glow: rgba(196, 30, 58, 0.5);
    --color-doctor: #228b22;
    --color-doctor-glow: rgba(34, 139, 34, 0.5);
    --color-detective: #6b3fa0;
    --color-detective-glow: rgba(107, 63, 160, 0.5);
    --color-villager: #b8860b;
    --color-villager-glow: rgba(184, 134, 11, 0.5);

    --color-alive: #50c878;
    --color-dead: #6e7681;
    --color-speaking: #f4cf47;

    --wood-medium: #4a3728;
    --text-muted: #6a5d4d;
  }

  /* Player Seat - Positioned absolutely */
  .player-seat {
    position: absolute;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: calc(0.35rem * var(--scale, 1));
    transform: translate(-50%, -50%);
    transition: all 0.4s ease;
    animation: seatAppear 0.6s ease-out backwards;
    cursor: pointer;
    outline: none;
    /* Use scale factor for proportional sizing */
    --base-scale: var(--scale, 1);
    /* Ensure player seats render above the table surface (wooden ring & felt) */
    z-index: 10;
  }

  .player-seat.hovered {
    z-index: 9999;
  }

  .player-seat.hovered .player-avatar {
    transform: scale(1.08);
    border-color: var(--noir-gold-bright);
    box-shadow:
      0 0 20px rgba(212, 175, 55, 0.4),
      0 8px 20px rgba(0, 0, 0, 0.4);
  }

  @keyframes seatAppear {
    from {
      opacity: 0;
      transform: translate(-50%, -50%) scale(0.8);
    }
    to {
      opacity: 1;
      transform: translate(-50%, -50%) scale(1);
    }
  }

  /* Avatar Container */
  .player-avatar-container {
    position: relative;
  }

  /* Avatar Circle - Larger base size, scales with table */
  .player-avatar {
    width: calc(80px * var(--base-scale));
    height: calc(80px * var(--base-scale));
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: calc(2rem * var(--base-scale));
    border: 3px solid var(--noir-gold-dim);
    transition: all 0.4s ease;
    cursor: pointer;
    background: var(--noir-charcoal);
    box-shadow:
      0 4px 12px rgba(0, 0, 0, 0.5),
      inset 0 1px 0 rgba(255, 255, 255, 0.05);
    position: relative;
  }

  /* Ornate Frame Effect */
  .player-avatar::before {
    content: '';
    position: absolute;
    top: calc(-5px * var(--base-scale));
    left: calc(-5px * var(--base-scale));
    right: calc(-5px * var(--base-scale));
    bottom: calc(-5px * var(--base-scale));
    border: 1px solid var(--noir-gold-dim);
    border-radius: 6px;
    opacity: 0.4;
  }

  .avatar-emoji {
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
  }

  /* Role-specific Avatar Styling */
  .player-seat.mafia .player-avatar {
    background: linear-gradient(135deg, var(--noir-burgundy-deep) 0%, var(--noir-charcoal) 100%);
    border-color: var(--color-mafia);
    box-shadow:
      0 4px 12px var(--color-mafia-glow),
      inset 0 0 15px rgba(196, 30, 58, 0.2);
  }

  .player-seat.doctor .player-avatar {
    background: linear-gradient(135deg, rgba(34, 139, 34, 0.3) 0%, var(--noir-charcoal) 100%);
    border-color: var(--color-doctor);
    box-shadow:
      0 4px 12px var(--color-doctor-glow),
      inset 0 0 15px rgba(34, 139, 34, 0.2);
  }

  .player-seat.detective .player-avatar {
    background: linear-gradient(135deg, rgba(107, 63, 160, 0.3) 0%, var(--noir-charcoal) 100%);
    border-color: var(--color-detective);
    box-shadow:
      0 4px 12px var(--color-detective-glow),
      inset 0 0 15px rgba(107, 63, 160, 0.2);
  }

  .player-seat.villager .player-avatar {
    background: linear-gradient(135deg, rgba(184, 134, 11, 0.2) 0%, var(--noir-charcoal) 100%);
    border-color: var(--color-villager);
    box-shadow:
      0 4px 12px var(--color-villager-glow),
      inset 0 0 15px rgba(184, 134, 11, 0.15);
  }

  /* Status Indicator Dot */
  .status-indicator {
    position: absolute;
    top: calc(-3px * var(--base-scale));
    right: calc(-3px * var(--base-scale));
    width: calc(14px * var(--base-scale));
    height: calc(14px * var(--base-scale));
    border-radius: 50%;
    border: 2px solid var(--noir-charcoal);
    z-index: 2;
  }

  .status-indicator.alive {
    background: var(--color-alive);
    box-shadow: 0 0 6px var(--color-alive);
  }

  /* Dead Player - Ghost Effect */
  .player-seat.dead {
    animation: deathFade 1s ease-out forwards;
  }

  @keyframes deathFade {
    0% { filter: none; }
    50% { filter: brightness(2) saturate(0); }
    100% { filter: saturate(0) brightness(0.6); }
  }

  .player-seat.dead .player-avatar {
    opacity: 0.5;
    filter: grayscale(1) brightness(0.7);
    border-color: var(--color-dead);
    box-shadow:
      0 0 25px rgba(255, 255, 255, 0.1),
      inset 0 0 15px rgba(0, 0, 0, 0.5);
    animation: ghostFloat 3s ease-in-out infinite;
  }

  @keyframes ghostFloat {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-3px); }
  }

  /* Death Marker R.I.P. */
  .player-seat.dead::after {
    content: 'R.I.P';
    position: absolute;
    top: calc(-12px * var(--base-scale));
    left: 50%;
    transform: translateX(-50%);
    font-family: 'Playfair Display', serif;
    font-size: calc(0.7rem * var(--base-scale));
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--text-muted);
    background: var(--noir-charcoal);
    padding: calc(0.1rem * var(--base-scale)) calc(0.4rem * var(--base-scale));
    border: 1px solid var(--color-dead);
    border-radius: 2px;
    z-index: 5;
  }

  /* Speaking Indicator - Gold Glow Pulse */
  .player-seat.speaking .player-avatar {
    animation: speakingGlow 1.5s ease-in-out infinite;
    border-color: var(--color-speaking);
  }

  @keyframes speakingGlow {
    0%, 100% {
      box-shadow:
        0 0 12px rgba(244, 207, 71, 0.5),
        0 0 25px rgba(244, 207, 71, 0.3);
    }
    50% {
      box-shadow:
        0 0 20px rgba(244, 207, 71, 0.7),
        0 0 40px rgba(244, 207, 71, 0.4);
    }
  }

  /* Player Name - Brass Nameplate - Larger, more readable */
  .player-name-tag {
    background: linear-gradient(180deg, var(--noir-gold-dim) 0%, var(--wood-medium) 100%);
    padding: calc(0.25rem * var(--base-scale)) calc(0.6rem * var(--base-scale));
    border-radius: 2px;
    font-family: 'Bebas Neue', sans-serif;
    font-size: calc(0.85rem * var(--base-scale));
    font-weight: 400;
    letter-spacing: 0.08em;
    color: var(--noir-black);
    white-space: nowrap;
    border: 1px solid var(--noir-gold);
    max-width: calc(120px * var(--base-scale));
    overflow: hidden;
    text-overflow: ellipsis;
    text-transform: uppercase;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  }

  .player-seat.dead .player-name-tag {
    opacity: 0.5;
    text-decoration: line-through;
    filter: grayscale(1);
  }

  /* Role Label - Larger, more readable */
  .player-role-tag {
    font-family: 'Cormorant Garamond', serif;
    font-size: calc(0.8rem * var(--base-scale));
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-style: italic;
  }

  .player-seat.mafia .player-role-tag { color: var(--color-mafia); }
  .player-seat.doctor .player-role-tag { color: var(--color-doctor); }
  .player-seat.detective .player-role-tag { color: var(--color-detective); }
  .player-seat.villager .player-role-tag { color: var(--color-villager); }
</style>
