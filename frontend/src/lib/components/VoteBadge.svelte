<script lang="ts">
  interface Props {
    voterName: string;
    voterRole: string;
    index: number;
    scaleFactor: number;
  }

  let { voterName, voterRole, index, scaleFactor }: Props = $props();

  const roleEmoji: Record<string, string> = {
    mafia: '🔪',
    doctor: '💊',
    deputy: '🔍',
    townsperson: '👤'
  };

  const emoji = $derived(roleEmoji[voterRole] || '👤');
</script>

<div
  class="vote-badge {voterRole}"
  style="--index: {index}; --scale: {scaleFactor};"
  title={voterName}
>
  <span class="badge-emoji">{emoji}</span>
</div>

<style>
  .vote-badge {
    width: calc(28px * var(--scale, 1));
    height: calc(28px * var(--scale, 1));
    border-radius: 50%;
    background: var(--noir-charcoal, #141412);
    border: 2px solid var(--noir-gold-dim, #a68829);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: calc(0.75rem * var(--scale, 1));
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.5);
    animation: badgeAppear 0.4s ease-out backwards;
    animation-delay: calc(var(--index, 0) * 0.08s);
    cursor: default;
    transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.4s ease, border-color 0.4s ease;
  }

  .vote-badge:hover {
    transform: scale(1.15);
    box-shadow: 0 4px 12px var(--accent-glow, rgba(212, 175, 55, 0.4));
  }

  .vote-badge.mafia {
    border-color: var(--color-mafia, #c41e3a);
    box-shadow: 0 2px 6px var(--color-mafia-glow, rgba(196, 30, 58, 0.4));
  }

  .vote-badge.doctor {
    border-color: var(--color-doctor, #228b22);
    box-shadow: 0 2px 6px var(--color-doctor-glow, rgba(34, 139, 34, 0.4));
  }

  .vote-badge.deputy {
    border-color: var(--color-detective, #6b3fa0);
    box-shadow: 0 2px 6px var(--color-detective-glow, rgba(107, 63, 160, 0.4));
  }

  .vote-badge.villager,
  .vote-badge.townsperson {
    border-color: var(--color-villager, #b8860b);
    box-shadow: 0 2px 6px var(--color-villager-glow, rgba(184, 134, 11, 0.4));
  }

  .badge-emoji {
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
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
