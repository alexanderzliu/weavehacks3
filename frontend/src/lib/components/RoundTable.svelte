<script lang="ts">
  import PlayerSeat from './PlayerSeat.svelte';
  import SpeechBubble from './SpeechBubble.svelte';
  import VoteArrow from './VoteArrow.svelte';
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
    onPlayerHover
  }: Props = $props();

  // Calculate circular positions for players
  const tableSize = 580;
  const radius = 240;
  const centerX = 290;
  const centerY = 290;

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
</script>

<div class="table-section">
  <!-- Overhead lamp glow effect -->
  <div class="lamp-glow"></div>

  <div class="round-table-container">
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
      />
    {/each}

    <!-- Speech bubble centered on table -->
    {#if currentSpeakerId && speechContent}
      <SpeechBubble
        speakerName={speakerName || 'Unknown'}
        content={speechContent}
        speakerPosition={getPlayerPosition(currentSpeakerId)}
        tableCenter={{ x: centerX, y: centerY }}
      />
    {/if}

    <!-- Vote arrows SVG layer -->
    <svg class="vote-arrows-layer">
      {#each [...votes.entries()] as [voterId, targetId]}
        {@const fromPos = getPlayerPosition(voterId)}
        {@const toPos = getPlayerPosition(targetId)}
        {#if fromPos && toPos}
          <VoteArrow
            fromPosition={{ x: fromPos.x, y: fromPos.y }}
            toPosition={{ x: toPos.x, y: toPos.y }}
          />
        {/if}
      {/each}
    </svg>
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
  }

  /* Overhead Lamp Glow */
  .lamp-glow {
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 400px;
    height: 250px;
    background: radial-gradient(ellipse at top, rgba(212, 175, 55, 0.06) 0%, transparent 70%);
    pointer-events: none;
    z-index: 1;
  }

  /* Round Table Container */
  .round-table-container {
    position: relative;
    width: 580px;
    height: 580px;
    z-index: 2;
  }

  /* Outer Wooden Ring */
  .round-table-container::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 420px;
    height: 420px;
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

  /* Green Felt Center */
  .round-table-container::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 340px;
    height: 340px;
    background: radial-gradient(ellipse at center, var(--felt-green) 0%, var(--felt-green-dark) 100%);
    border-radius: 50%;
    border: 3px solid var(--noir-gold-dim);
    box-shadow:
      inset 0 0 60px rgba(0, 0, 0, 0.4),
      inset 0 0 120px rgba(0, 0, 0, 0.2);
    z-index: 1;
  }

  /* Vote Arrows SVG Layer */
  .vote-arrows-layer {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 50;
    overflow: visible;
  }

  /* Responsive adjustments */
  @media (max-width: 1200px) {
    .round-table-container {
      width: 520px;
      height: 520px;
    }

    .round-table-container::before {
      width: 380px;
      height: 380px;
    }

    .round-table-container::after {
      width: 300px;
      height: 300px;
    }
  }

  @media (max-width: 900px) {
    .round-table-container {
      width: 450px;
      height: 450px;
    }

    .round-table-container::before {
      width: 320px;
      height: 320px;
    }

    .round-table-container::after {
      width: 250px;
      height: 250px;
    }
  }

  @media (max-width: 600px) {
    .table-section {
      min-height: 400px;
    }

    .round-table-container {
      width: 350px;
      height: 350px;
    }

    .round-table-container::before {
      width: 250px;
      height: 250px;
    }

    .round-table-container::after {
      width: 190px;
      height: 190px;
    }
  }
</style>
