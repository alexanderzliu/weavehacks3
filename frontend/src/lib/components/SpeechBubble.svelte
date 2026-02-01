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

  // Default speed when no audio (fallback)
  const DEFAULT_CHARS_PER_SECOND = 50;
  // Clamp speeds to reasonable bounds
  const MIN_CHARS_PER_SECOND = 15;  // Don't go too slow
  const MAX_CHARS_PER_SECOND = 120; // Don't go too fast

  // Track last seen content to detect changes
  let lastSeenContent = $state<string | null>(null);

  // Truncate helper
  function truncate(text: string): string {
    return text.length > 800 ? text.slice(0, 797) + '...' : text;
  }

  // Parse WAV header to get audio duration in seconds
  function getWavDuration(base64: string): number | null {
    try {
      const binary = atob(base64);

      // WAV header structure (little-endian):
      // Bytes 24-27: Sample rate
      // Bytes 28-31: Byte rate (sample rate * channels * bytes per sample)
      // Bytes 34-35: Bits per sample
      // Bytes 40-43: Data chunk size (after "data" marker)

      // Read sample rate (bytes 24-27, little-endian)
      const sampleRate =
        binary.charCodeAt(24) |
        (binary.charCodeAt(25) << 8) |
        (binary.charCodeAt(26) << 16) |
        (binary.charCodeAt(27) << 24);

      // Read number of channels (bytes 22-23, little-endian)
      const numChannels = binary.charCodeAt(22) | (binary.charCodeAt(23) << 8);

      // Read bits per sample (bytes 34-35, little-endian)
      const bitsPerSample = binary.charCodeAt(34) | (binary.charCodeAt(35) << 8);

      // Find the "data" chunk - it starts after the format chunk
      // Usually at byte 36, but can vary if there are extra chunks
      let dataOffset = 36;
      while (dataOffset < binary.length - 8) {
        const chunkId = binary.slice(dataOffset, dataOffset + 4);
        if (chunkId === 'data') {
          // Read data size (next 4 bytes, little-endian)
          const dataSize =
            binary.charCodeAt(dataOffset + 4) |
            (binary.charCodeAt(dataOffset + 5) << 8) |
            (binary.charCodeAt(dataOffset + 6) << 16) |
            (binary.charCodeAt(dataOffset + 7) << 24);

          // Calculate duration
          const bytesPerSample = bitsPerSample / 8;
          const duration = dataSize / (sampleRate * numChannels * bytesPerSample);
          return duration;
        }
        // Move to next chunk (chunk header is 8 bytes + chunk size)
        const chunkSize =
          binary.charCodeAt(dataOffset + 4) |
          (binary.charCodeAt(dataOffset + 5) << 8) |
          (binary.charCodeAt(dataOffset + 6) << 16) |
          (binary.charCodeAt(dataOffset + 7) << 24);
        dataOffset += 8 + chunkSize;
      }

      return null; // Couldn't find data chunk
    } catch {
      return null;
    }
  }

  // The target content to stream
  let targetContent = $derived(truncate(content));

  // Track current audio for cleanup
  let currentAudio: HTMLAudioElement | null = null;

  // Track completion states for synchronization
  let audioComplete = $state(false);
  let typewriterComplete = $state(false);

  // Start streaming when content changes
  $effect(() => {
    const newContent = content;

    // Only restart if content actually changed
    if (newContent === lastSeenContent) return;
    lastSeenContent = newContent;

    // Reset state
    displayedCharCount = 0;
    audioComplete = false;
    typewriterComplete = false;

    // Clear any existing interval
    if (typewriterInterval) {
      clearInterval(typewriterInterval);
      typewriterInterval = null;
    }

    // Stop any playing audio
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    const target = truncate(newContent);

    // Calculate typewriter speed based on audio duration
    let intervalMs = 1000 / DEFAULT_CHARS_PER_SECOND;

    if (audioBase64) {
      const audioDuration = getWavDuration(audioBase64);

      if (audioDuration && audioDuration > 0 && target.length > 0) {
        // Sync typewriter to audio duration
        const charsPerSecond = target.length / audioDuration;
        // Clamp to reasonable bounds
        const clampedSpeed = Math.max(MIN_CHARS_PER_SECOND, Math.min(MAX_CHARS_PER_SECOND, charsPerSecond));
        intervalMs = 1000 / clampedSpeed;
      }

      // Play audio
      try {
        currentAudio = new Audio(`data:audio/wav;base64,${audioBase64}`);
        currentAudio.onerror = (e) => {
          console.error('[SpeechBubble] Audio decode error:', e);
          audioComplete = true;
          maybeComplete();
        };
        currentAudio.onended = () => {
          audioComplete = true;
          maybeComplete();
        };
        currentAudio.play().catch((err) => {
          console.warn('[SpeechBubble] Audio playback blocked:', err.name, err.message);
          audioComplete = true;
          maybeComplete();
        });
      } catch (err) {
        console.error('[SpeechBubble] Audio creation failed:', err);
        audioComplete = true;
      }
    } else {
      // No audio, mark as complete
      audioComplete = true;
    }

    // Helper to check if both are done
    function maybeComplete() {
      if (audioComplete && typewriterComplete) {
        onStreamComplete?.();
      }
    }

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
        typewriterComplete = true;
        maybeComplete();
      }
    }, intervalMs);
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
