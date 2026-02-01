<script lang="ts">
  interface Props {
    fromPosition: { x: number; y: number };
    toPosition: { x: number; y: number };
  }

  let { fromPosition, toPosition }: Props = $props();

  // Calculate arrow path with offsets to avoid avatar overlap
  const startOffset = 38; // Start outside voter avatar
  const endOffset = 42; // End before target avatar

  let arrowPath = $derived.by(() => {
    const dx = toPosition.x - fromPosition.x;
    const dy = toPosition.y - fromPosition.y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance === 0) return '';

    // Normalize direction
    const nx = dx / distance;
    const ny = dy / distance;

    // Start and end points with offsets
    const startX = fromPosition.x + nx * startOffset;
    const startY = fromPosition.y + ny * startOffset;
    const endX = toPosition.x - nx * endOffset;
    const endY = toPosition.y - ny * endOffset;

    return `M ${startX} ${startY} L ${endX} ${endY}`;
  });

  // Calculate path length for stroke animation
  let pathLength = $derived.by(() => {
    const dx = toPosition.x - fromPosition.x;
    const dy = toPosition.y - fromPosition.y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance === 0) return 0;

    // Account for offsets
    return Math.max(0, distance - startOffset - endOffset);
  });

  // Generate unique ID for the arrowhead marker
  let markerId = $derived(`arrowhead-${Math.random().toString(36).substr(2, 9)}`);
</script>

<g class="vote-arrow-group">
  <!-- Arrowhead marker definition -->
  <defs>
    <marker
      id={markerId}
      markerWidth="10"
      markerHeight="7"
      refX="9"
      refY="3.5"
      orient="auto"
    >
      <polygon points="0 0, 10 3.5, 0 7" class="arrow-head" />
    </marker>
  </defs>

  <!-- Arrow line -->
  {#if arrowPath}
    <path
      d={arrowPath}
      class="vote-arrow"
      marker-end="url(#{markerId})"
      style="stroke-dasharray: {pathLength}; stroke-dashoffset: {pathLength};"
    />
  {/if}
</g>

<style>
  .vote-arrow {
    stroke: #d4af37;
    stroke-width: 2.5;
    fill: none;
    filter: drop-shadow(0 0 5px rgba(212, 175, 55, 0.6));
    stroke-linecap: round;
    animation: drawArrow 0.5s ease-out forwards;
  }

  @keyframes drawArrow {
    to {
      stroke-dashoffset: 0;
    }
  }

  .arrow-head {
    fill: #d4af37;
    filter: drop-shadow(0 0 4px rgba(212, 175, 55, 0.6));
    animation: arrowHeadAppear 0.3s ease-out 0.4s forwards;
    opacity: 0;
  }

  @keyframes arrowHeadAppear {
    to {
      opacity: 1;
    }
  }
</style>
