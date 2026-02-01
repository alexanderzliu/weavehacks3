<script lang="ts">
  import { onDestroy } from 'svelte';

  interface Props {
    speakerName: string;
    content: string;
    scaleFactor?: number;
  }

  interface QueuedSpeech {
    speakerName: string;
    content: string;
  }

  let { speakerName, content, scaleFactor = 1 }: Props = $props();

  // Queue of speeches waiting to be displayed
  let speechQueue = $state<QueuedSpeech[]>([]);

  // Currently displaying speech (separate from props)
  let currentSpeech = $state<QueuedSpeech | null>(null);

  // Typewriter effect state
  let displayedCharCount = $state(0);
  let typewriterInterval: ReturnType<typeof setInterval> | null = null;
  let postStreamDelay: ReturnType<typeof setTimeout> | null = null;
  const CHARS_PER_SECOND = 50;
  const INTERVAL_MS = 1000 / CHARS_PER_SECOND; // 20ms per character
  const POST_STREAM_DELAY_MS = 500; // Brief pause after streaming before next speech

  // Track last seen content to detect new speeches
  let lastSeenContent = $state<string | null>(null);

  // Truncate helper
  function truncate(text: string): string {
    return text.length > 800 ? text.slice(0, 797) + '...' : text;
  }

  // Process the next speech in queue
  function processNextSpeech() {
    if (speechQueue.length === 0) {
      return;
    }

    // Pop the first speech from queue
    const next = speechQueue[0];
    speechQueue = speechQueue.slice(1);
    currentSpeech = next;
    displayedCharCount = 0;

    // Clear any existing interval
    if (typewriterInterval) {
      clearInterval(typewriterInterval);
      typewriterInterval = null;
    }

    const targetContent = truncate(next.content);

    // Start streaming
    typewriterInterval = setInterval(() => {
      if (displayedCharCount < targetContent.length) {
        displayedCharCount++;
      } else {
        // Done streaming
        if (typewriterInterval) {
          clearInterval(typewriterInterval);
          typewriterInterval = null;
        }

        // Wait briefly, then process next speech if any
        postStreamDelay = setTimeout(() => {
          postStreamDelay = null;
          if (speechQueue.length > 0) {
            processNextSpeech();
          }
        }, POST_STREAM_DELAY_MS);
      }
    }, INTERVAL_MS);
  }

  // When props change, queue the new speech
  $effect(() => {
    // Access props to create dependency
    const newContent = content;
    const newSpeaker = speakerName;

    // Only queue if this is actually new content
    if (newContent && newContent !== lastSeenContent) {
      lastSeenContent = newContent;

      const newSpeech: QueuedSpeech = {
        speakerName: newSpeaker,
        content: newContent
      };

      // If nothing is currently playing, start immediately
      if (!currentSpeech && speechQueue.length === 0) {
        speechQueue = [newSpeech];
        processNextSpeech();
      } else {
        // Add to queue
        speechQueue = [...speechQueue, newSpeech];
      }
    }
  });

  // Cleanup on destroy
  onDestroy(() => {
    if (typewriterInterval) {
      clearInterval(typewriterInterval);
    }
    if (postStreamDelay) {
      clearTimeout(postStreamDelay);
    }
  });

  // The visible content based on typewriter progress
  let displayContent = $derived(
    currentSpeech ? truncate(currentSpeech.content).slice(0, displayedCharCount) : ''
  );

  // The currently displayed speaker name
  let displaySpeaker = $derived(currentSpeech?.speakerName || speakerName);
</script>

<div class="speech-bubble-container" style="--scale: {scaleFactor};">
  <div class="speech-bubble">
    <div class="bubble-header">
      <span class="speaker-name">{displaySpeaker}</span>
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
    background: #f5e6c8;
    color: #0a0908;
    border-radius: 12px;
    font-family: 'Cormorant Garamond', Georgia, serif;
    font-size: 0.85rem;
    font-weight: 500;
    line-height: 1.4;
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
