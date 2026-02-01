<script lang="ts">
  import { onMount } from 'svelte';
  import PlayerSeat from './PlayerSeat.svelte';
  import SpeechBubble from './SpeechBubble.svelte';
  import VoteBadgeCluster from './VoteBadgeCluster.svelte';
  import type { Cheatsheet } from '$lib/types';

  interface Player {
    id: string;
    name: string;
    role?: string;
    is_alive: boolean;
    playerId?: string; // UUID from backend
  }

  interface Props {
    players: Player[];
    currentSpeakerId: string | null;
    speechContent: string | null;
    speakerName: string | null;
    votes: Map<string, string>; // voterId -> targetId
    showRoles?: boolean;
    cheatsheets?: Map<string, Cheatsheet>; // playerId -> cheatsheet
    loadingCheatsheet?: string | null; // playerId currently loading
    onPlayerHover?: (playerId: string | null) => void;
    onSpeechComplete?: () => void;
    speechBubbleKey?: number; // Key to force SpeechBubble re-render
  }

  let {
    players,
    currentSpeakerId,
    speechContent,
    speakerName,
    votes,
    showRoles = false,
    cheatsheets = new Map(),
    loadingCheatsheet = null,
    onPlayerHover,
    onSpeechComplete,
    speechBubbleKey = 0
  }: Props = $props();

  // Responsive table sizing
  let containerEl: HTMLDivElement;
  let tableSize = $state(580);

  // Padding for player cards (so they don't overflow the container)
  // Increased to account for name tags, role labels, and R.I.P markers
  const playerCardPadding = 80; // Space for cards that extend beyond their center point

  onMount(() => {
    const updateSize = () => {
      if (containerEl) {
        // Get available space, accounting for padding needed for player cards
        const rect = containerEl.getBoundingClientRect();
        const availableSize = Math.min(rect.width, rect.height) - (playerCardPadding * 2);
        // Clamp between reasonable min/max (increased max to compensate for tighter radius)
        tableSize = Math.max(400, Math.min(850, availableSize));
      }
    };

    updateSize();
    const resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(containerEl);

    return () => resizeObserver.disconnect();
  });

  // Dynamic calculations based on table size
  // Reduced radius to keep player cards (including labels below) inside the container
  let radius = $derived(tableSize * 0.36); // ~36% of table size for player radius
  let centerX = $derived(tableSize / 2);
  let centerY = $derived(tableSize / 2);

  // Scale factor for player card sizing (1 = base size at 580px)
  let scaleFactor = $derived(tableSize / 580);

  let positions = $derived.by(() => {
    const numPlayers = players.length;
    return players.map((_, index) => {
      const angle = (-90 + (360 / numPlayers) * index) * (Math.PI / 180);
      return {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      };
    });
  });

  // Get position for a player by ID
  function getPlayerPosition(playerId: string): { x: number; y: number } | null {
    const index = players.findIndex((p) => p.id === playerId);
    if (index === -1) return null;
    return positions[index];
  }

  // Aggregate votes by target for badge clusters
  let votesByTarget = $derived.by(() => {
    const result = new Map<string, Array<{ id: string; name: string; role: string }>>();
    for (const [voterId, targetId] of votes) {
      const voter = players.find((p) => p.id === voterId);
      if (!voter) continue;
      const existing = result.get(targetId) || [];
      existing.push({
        id: voterId,
        name: voter.name,
        role: voter.role || 'townsperson'
      });
      result.set(targetId, existing);
    }
    return result;
  });
</script>

<div class="table-section" bind:this={containerEl}>
  <!-- Overhead lamp glow effect -->
  <div class="lamp-glow"></div>

  <div
    class="round-table-container"
    style="width: {tableSize}px; height: {tableSize}px; --table-size: {tableSize}px; --scale: {scaleFactor};"
  >
    <!-- Wooden outer ring (::before pseudo-element in CSS) -->
    <!-- Green felt center (::after pseudo-element in CSS) -->

    <!-- Player seats -->
    {#each players as player, index}
      <PlayerSeat
        name={player.name}
        playerId={player.playerId}
        role={showRoles && player.role ? player.role : 'townsperson'}
        isAlive={player.is_alive}
        isSpeaking={player.id === currentSpeakerId}
        position={positions[index]}
        tableCenter={{ x: centerX, y: centerY }}
        cheatsheet={player.playerId ? cheatsheets.get(player.playerId) : null}
        cheatsheetLoading={loadingCheatsheet === player.playerId}
        onHover={onPlayerHover}
        {scaleFactor}
      />
    {/each}

    <!-- Speech bubble centered on table -->
    {#if currentSpeakerId && speechContent}
      {#key speechBubbleKey}
        <SpeechBubble
          speakerName={speakerName || 'Unknown'}
          content={speechContent}
          {scaleFactor}
          onStreamComplete={onSpeechComplete}
        />
      {/key}
    {/if}

    <!-- Vote badge clusters -->
    {#each [...votesByTarget.entries()] as [targetId, voters] (targetId)}
      {@const targetPos = getPlayerPosition(targetId)}
      {#if targetPos}
        <VoteBadgeCluster
          {voters}
          targetPosition={targetPos}
          {scaleFactor}
        />
      {/if}
    {/each}
  </div>
</div>

<style>
  /* CSS Variables - Noir Palette */
  :root {
    --noir-black: #0a0908;
    --noir-charcoal: #141412;
    --noir-dark: #1a1917;
    --noir-gold: #d4af37;
    --noir-gold-dim: #a68829;
    --noir-gold-bright: #f4cf47;
    --border-gold: #8b7355;
    --shadow-noir: 0 10px 40px rgba(0, 0, 0, 0.6);

    /* Felt & Wood */
    --felt-green: #1a4d2e;
    --felt-green-dark: #0f2d1a;
    --wood-dark: #2a1f14;
    --wood-medium: #4a3728;
    --wood-light: #6a5040;
  }

  /* Table Section - Primary Focus */
  .table-section {
    flex: 1;
    min-height: 500px;
    background: linear-gradient(180deg, var(--noir-dark) 0%, var(--noir-charcoal) 100%);
    border-radius: 4px;
    border: 1px solid var(--border-gold);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    box-shadow: var(--shadow-noir);
    overflow: visible;
    /* Add padding to prevent player cards from overflowing */
    padding: 80px;
  }

  /* Overhead Lamp Glow */
  .lamp-glow {
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 60%;
    height: 250px;
    background: radial-gradient(ellipse at top, rgba(212, 175, 55, 0.06) 0%, transparent 70%);
    pointer-events: none;
    z-index: 1;
  }

  /* Round Table Container - Now fluid */
  .round-table-container {
    position: relative;
    z-index: 2;
    /* Width/height set via inline style */
  }

  /* Outer Wooden Ring - Scales with table */
  .round-table-container::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    /* ~72% of table size */
    width: calc(var(--table-size, 580px) * 0.72);
    height: calc(var(--table-size, 580px) * 0.72);
    background:
      radial-gradient(ellipse at 30% 30%, var(--wood-light) 0%, transparent 50%),
      radial-gradient(ellipse at 70% 70%, var(--wood-dark) 0%, transparent 50%),
      linear-gradient(45deg, var(--wood-medium) 0%, var(--wood-dark) 50%, var(--wood-medium) 100%);
    border-radius: 50%;
    border: 4px solid var(--noir-gold-dim);
    box-shadow:
      inset 0 0 40px rgba(0, 0, 0, 0.5),
      0 0 0 2px var(--wood-dark),
      0 0 50px rgba(0, 0, 0, 0.5),
      0 0 80px rgba(212, 175, 55, 0.08);
    z-index: 0;
  }

  /* Green Felt Center - Scales with table */
  .round-table-container::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    /* ~59% of table size */
    width: calc(var(--table-size, 580px) * 0.59);
    height: calc(var(--table-size, 580px) * 0.59);
    background: radial-gradient(ellipse at center, var(--felt-green) 0%, var(--felt-green-dark) 100%);
    border-radius: 50%;
    border: 3px solid var(--noir-gold-dim);
    box-shadow:
      inset 0 0 60px rgba(0, 0, 0, 0.4),
      inset 0 0 120px rgba(0, 0, 0, 0.2);
    z-index: 1;
  }

  /* Responsive adjustments - now handled dynamically via JS */
  @media (max-width: 600px) {
    .table-section {
      min-height: 400px;
      padding: 40px;
    }
  }
</style>
