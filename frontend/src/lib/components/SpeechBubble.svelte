<script lang="ts">
  import { onDestroy } from 'svelte';

  interface Props {
    speakerName: string;
    content: string;
    audioBase64?: string | null;
    scaleFactor?: number;
    onStreamComplete?: () => void;
  }

  let { speakerName, content, audioBase64 = null, scaleFactor = 1, onStreamComplete }: Props = $props();

  // Typewriter effect state
  let displayedCharCount = $state(0);
  let typewriterInterval: ReturnType<typeof setInterval> | null = null;
  const CHARS_PER_SECOND = 50;
  const INTERVAL_MS = 1000 / CHARS_PER_SECOND; // 20ms per character

  // Track last seen content to detect changes
  let lastSeenContent = $state<string | null>(null);

  // Truncate helper
  function truncate(text: string): string {
    return text.length > 800 ? text.slice(0, 797) + '...' : text;
  }

  // The target content to stream
  let targetContent = $derived(truncate(content));

  // Track current audio for cleanup
  let currentAudio: HTMLAudioElement | null = null;

  // Start streaming when content changes
  $effect(() => {
    const newContent = content;

    // Only restart if content actually changed
    if (newContent === lastSeenContent) return;
    lastSeenContent = newContent;

    // Reset
    displayedCharCount = 0;

    // Clear any existing interval
    if (typewriterInterval) {
      clearInterval(typewriterInterval);
      typewriterInterval = null;
    }

    // Stop any playing audio and play new audio if available
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
    if (audioBase64) {
      try {
        currentAudio = new Audio(`data:audio/wav;base64,${audioBase64}`);
        currentAudio.play().catch(() => {}); // Silent failure
      } catch {}
    }

    const target = truncate(newContent);

    // Start streaming
    typewriterInterval = setInterval(() => {
      if (displayedCharCount < target.length) {
        displayedCharCount++;
      } else {
        // Done streaming
        if (typewriterInterval) {
          clearInterval(typewriterInterval);
          typewriterInterval = null;
        }
        // Notify parent that streaming is complete
        onStreamComplete?.();
      }
    }, INTERVAL_MS);
  });

  // Cleanup on destroy
  onDestroy(() => {
    if (typewriterInterval) {
      clearInterval(typewriterInterval);
    }
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
  });

  // The visible content based on typewriter progress
  let displayContent = $derived(targetContent.slice(0, displayedCharCount));
</script>

<div class="speech-bubble-container" style="--scale: {scaleFactor};">
  <div class="speech-bubble">
    <div class="bubble-header">
      <span class="speaker-name">{speakerName}</span>
    </div>
    <div class="bubble-content">
      {displayContent}
    </div>
  </div>
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
    /* Scale max-width with table size - base 280px at scale 1, up to ~400px at larger scales */
    max-width: calc(280px * var(--scale, 1));
    min-width: 200px;
    padding: 0.8rem 1rem;
    background: var(--noir-cream, #f5e6c8);
    color: var(--noir-black, #0a0908);
    border-radius: 12px;
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 0.85rem;
    font-weight: 500;
    line-height: 1.4;
    text-align: center;
    box-shadow:
      0 6px 20px rgba(0, 0, 0, 0.5),
      0 0 0 2px var(--noir-gold-dim, #a68829);
    animation: bubbleAppear 0.3s ease-out;
    transition: background 0.4s ease, color 0.4s ease, box-shadow 0.4s ease;
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
    color: var(--noir-gold, #d4af37);
    transition: color 0.4s ease;
  }

  .bubble-content {
    color: var(--noir-black, #0a0908);
    transition: color 0.4s ease;
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
