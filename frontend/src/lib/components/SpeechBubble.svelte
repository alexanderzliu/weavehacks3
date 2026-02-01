<script lang="ts">
  interface Props {
    speakerName: string;
    content: string;
    speakerPosition: { x: number; y: number } | null;
    tableCenter: { x: number; y: number };
  }

  let { speakerName, content, speakerPosition, tableCenter }: Props = $props();

  // Truncate content to 120 chars
  let displayContent = $derived(
    content.length > 120 ? content.slice(0, 117) + '...' : content
  );

  // Calculate SVG tail path from bubble edge to speaker
  let tailPath = $derived.by(() => {
    if (!speakerPosition) return '';

    // Direction from center to speaker
    const dx = speakerPosition.x - tableCenter.x;
    const dy = speakerPosition.y - tableCenter.y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance === 0) return '';

    // Normalize direction
    const nx = dx / distance;
    const ny = dy / distance;

    // Start point (edge of bubble, about 70px from center)
    const startX = tableCenter.x + nx * 70;
    const startY = tableCenter.y + ny * 70;

    // End point (before speaker avatar, about 40px away)
    const endX = speakerPosition.x - nx * 40;
    const endY = speakerPosition.y - ny * 40;

    // Control point (perpendicular offset for curve)
    const perpX = -ny * 20;
    const perpY = nx * 20;
    const ctrlX = (startX + endX) / 2 + perpX;
    const ctrlY = (startY + endY) / 2 + perpY;

    return `M ${startX} ${startY} Q ${ctrlX} ${ctrlY} ${endX} ${endY}`;
  });
</script>

<div class="speech-bubble-container">
  <div class="speech-bubble">
    <div class="bubble-header">
      <span class="speaker-name">{speakerName}</span>
    </div>
    <div class="bubble-content">
      {displayContent}
    </div>
  </div>

  <!-- SVG tail pointing to speaker -->
  {#if tailPath}
    <svg class="bubble-tail-svg">
      <path d={tailPath} class="bubble-tail" />
    </svg>
  {/if}
</div>

<style>
  .speech-bubble-container {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 100;
    pointer-events: none;
  }

  .speech-bubble {
    max-width: 260px;
    padding: 0.8rem 1rem;
    background: #f5e6c8;
    color: #0a0908;
    border-radius: 12px;
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 0.9rem;
    font-weight: 500;
    line-height: 1.5;
    text-align: center;
    box-shadow:
      0 6px 20px rgba(0, 0, 0, 0.5),
      0 0 0 2px #a68829;
    animation: bubbleAppear 0.3s ease-out;
  }

  .bubble-header {
    margin-bottom: 0.4rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid rgba(0, 0, 0, 0.15);
  }

  .speaker-name {
    display: block;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 0.75rem;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #d4af37;
  }

  .bubble-content {
    color: #0a0908;
  }

  .bubble-tail-svg {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    overflow: visible;
  }

  .bubble-tail {
    stroke: #d4af37;
    stroke-width: 3;
    fill: none;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
  }

  @keyframes bubbleAppear {
    from {
      opacity: 0;
      transform: scale(0.8);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }
</style>
