<script lang="ts">
  import VoteBadge from './VoteBadge.svelte';

  interface Voter {
    id: string;
    name: string;
    role: string;
  }

  interface Props {
    voters: Voter[];
    targetPosition: { x: number; y: number };
    scaleFactor: number;
  }

  let { voters, targetPosition, scaleFactor }: Props = $props();

  const MAX_VISIBLE = 5;

  // Always position badges above the player for consistency
  const ABOVE_OFFSET = 55;

  // Calculate offset from target center (always above)
  let yOffset = $derived(-ABOVE_OFFSET * scaleFactor);

  // Visible voters (capped at MAX_VISIBLE)
  let visibleVoters = $derived(voters.slice(0, MAX_VISIBLE));
  let overflowCount = $derived(Math.max(0, voters.length - MAX_VISIBLE));
</script>

<div
  class="vote-cluster"
  style="
    left: {targetPosition.x}px;
    top: {targetPosition.y + yOffset}px;
    --scale: {scaleFactor};
  "
>
  <!-- Vote count pill -->
  <div class="vote-count">
    <span class="count-number">{voters.length}</span>
    <span class="count-label">{voters.length === 1 ? 'vote' : 'votes'}</span>
  </div>

  <!-- Voter badges -->
  <div class="badges-row">
    {#each visibleVoters as voter, i (voter.id)}
      <VoteBadge
        voterName={voter.name}
        voterRole={voter.role}
        index={i}
        {scaleFactor}
      />
    {/each}

    {#if overflowCount > 0}
      <div class="overflow-badge" style="--index: {visibleVoters.length}; --scale: {scaleFactor};">
        +{overflowCount}
      </div>
    {/if}
  </div>
</div>

<style>
  .vote-cluster {
    position: absolute;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column-reverse; /* Badges on top, count pill closer to player */
    align-items: center;
    gap: calc(6px * var(--scale, 1));
    z-index: 60;
    pointer-events: auto;
    animation: clusterAppear 0.3s ease-out;
  }

  .vote-count {
    display: flex;
    align-items: center;
    gap: calc(4px * var(--scale, 1));
    padding: calc(4px * var(--scale, 1)) calc(10px * var(--scale, 1));
    background: linear-gradient(135deg, #d4af37 0%, #a68829 100%);
    border-radius: calc(12px * var(--scale, 1));
    box-shadow:
      0 2px 8px rgba(0, 0, 0, 0.4),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);
    animation: countAppear 0.25s ease-out;
  }

  .count-number {
    font-family: 'Bebas Neue', sans-serif;
    font-size: calc(0.9rem * var(--scale, 1));
    font-weight: 400;
    color: #0a0908;
    letter-spacing: 0.02em;
  }

  .count-label {
    font-family: 'Cormorant Garamond', serif;
    font-size: calc(0.7rem * var(--scale, 1));
    font-weight: 500;
    color: #0a0908;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .badges-row {
    display: flex;
    justify-content: center;
    gap: calc(6px * var(--scale, 1));
  }

  .overflow-badge {
    width: calc(28px * var(--scale, 1));
    height: calc(28px * var(--scale, 1));
    border-radius: 50%;
    background: #1a1917;
    border: 2px solid #6a5d4d;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Bebas Neue', sans-serif;
    font-size: calc(0.7rem * var(--scale, 1));
    color: #a89880;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
    animation: badgeAppear 0.4s ease-out backwards;
    animation-delay: calc(var(--index, 0) * 0.08s);
  }

  @keyframes clusterAppear {
    0% {
      opacity: 0;
      transform: translateX(-50%) translateY(10px);
    }
    100% {
      opacity: 1;
      transform: translateX(-50%) translateY(0);
    }
  }

  @keyframes countAppear {
    0% {
      opacity: 0;
      transform: scale(0.8);
    }
    100% {
      opacity: 1;
      transform: scale(1);
    }
  }

  @keyframes badgeAppear {
    0% {
      opacity: 0;
      transform: scale(0.3) translateY(8px);
    }
    60% {
      opacity: 1;
      transform: scale(1.1) translateY(-2px);
    }
    100% {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }
</style>
