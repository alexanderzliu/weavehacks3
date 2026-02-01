"""Pipecat voice pipeline for human player in Mafia game.

This module provides real-time voice communication between a human player
and the game. It uses:
- Daily.co for WebRTC transport
- Deepgram for speech-to-text
- Cartesia for text-to-speech (AI player voices)
- Silero VAD for voice activity detection
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    Frame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transports.daily.transport import DailyParams, DailyTransport

from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class HumanSpeechResult:
    """Result of waiting for human speech."""

    text: str
    success: bool
    timed_out: bool = False


class TranscriptionCollector(FrameProcessor):
    """Collects transcription frames and notifies when speech is complete."""

    def __init__(
        self,
        on_transcription: Callable[[str], Awaitable[None]],
        on_speech_start: Callable[[], Awaitable[None]] | None = None,
    ):
        super().__init__()
        self._on_transcription = on_transcription
        self._on_speech_start = on_speech_start
        self._current_transcript = ""
        self._is_speaking = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame) and frame.text:
            # Final transcription received
            self._current_transcript = frame.text
            await self._on_transcription(frame.text)
            self._current_transcript = ""
            self._is_speaking = False

        # Pass frame downstream
        await self.push_frame(frame, direction)


class MafiaVoicePipeline:
    """Voice pipeline for human player in Mafia game.

    Handles:
    - Receiving human speech via WebRTC and transcribing with Deepgram
    - Playing AI speech via Cartesia TTS
    - Voice activity detection for natural turn-taking

    Turn-based: Only accepts speech when `_is_listening` is True.
    """

    def __init__(
        self,
        room_url: str,
        room_token: str,
        player_name: str = "Human",
    ):
        self.room_url = room_url
        self.room_token = room_token
        self.player_name = player_name

        self._pipeline: Pipeline | None = None
        self._task: PipelineTask | None = None
        self._runner: PipelineRunner | None = None
        self._transport: DailyTransport | None = None
        self._tts: CartesiaTTSService | None = None

        # Turn-based listening - only accept speech when True
        self._is_listening = False

        # Speech waiting
        self._speech_event = asyncio.Event()
        self._speech_result: HumanSpeechResult | None = None
        self._accumulated_text: list[str] = []  # Accumulate partial transcriptions
        self._speech_complete_event = asyncio.Event()  # Set when speech is truly complete
        self._speech_debounce_task: asyncio.Task | None = None
        self._speech_debounce_seconds = 2.5  # Wait this long after last speech

        # Callbacks
        self._on_human_speech: Callable[[str], Awaitable[None]] | None = None
        self._on_interrupt: Callable[[], Awaitable[None]] | None = None

    async def start(self) -> None:
        """Start the voice pipeline and connect to Daily room."""
        # Create transport
        self._transport = DailyTransport(
            self.room_url,
            self.room_token,
            self.player_name,
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
            ),
        )

        # Create STT service
        stt = DeepgramSTTService(
            api_key=settings.DEEPGRAM_API_KEY,
        )

        # Create TTS service
        self._tts = CartesiaTTSService(
            api_key=settings.CARTESIA_API_KEY,
            voice_id="a167e0f3-df7e-4d52-a9c3-f949145efdab",  # Default voice
        )

        # Create transcription collector
        collector = TranscriptionCollector(
            on_transcription=self._handle_transcription,
        )

        # Build pipeline: transport -> STT -> collector
        # TTS output goes back through transport
        self._pipeline = Pipeline(
            [
                self._transport.input(),
                stt,
                collector,
            ]
        )

        self._task = PipelineTask(
            self._pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=False,
            ),
        )

        self._runner = PipelineRunner()

        # Start in background
        asyncio.create_task(self._runner.run(self._task))

    async def stop(self) -> None:
        """Stop the voice pipeline."""
        if self._task:
            await self._task.cancel()
        if self._runner:
            await self._runner.stop()

    async def _handle_transcription(self, text: str) -> None:
        """Handle completed transcription from human.

        Only processes if we're actively listening (human's turn).
        Uses debouncing to wait for user to finish speaking before returning.
        """
        if not self._is_listening:
            # Ignore speech when it's not the human's turn
            logger.debug("Ignoring out-of-turn speech: %s...", text[:50])
            return

        # Accumulate transcription
        if text.strip():
            self._accumulated_text.append(text.strip())
            logger.debug("Received transcription: %s", text.strip())

        # Signal that we got some speech (for the first speech indicator)
        self._speech_event.set()

        # Cancel any existing debounce task and start a new one
        # This waits for a pause in speech before marking complete
        if self._speech_debounce_task:
            self._speech_debounce_task.cancel()

        self._speech_debounce_task = asyncio.create_task(self._debounce_speech_complete())

    async def _debounce_speech_complete(self) -> None:
        """Wait for speech to settle before marking complete."""
        try:
            await asyncio.sleep(self._speech_debounce_seconds)
            # No more speech came in during the debounce period
            if self._accumulated_text:
                full_text = " ".join(self._accumulated_text)
                self._speech_result = HumanSpeechResult(text=full_text, success=True)
                logger.debug("Speech complete after debounce: %s...", full_text[:100])
                self._speech_complete_event.set()

                if self._on_human_speech:
                    await self._on_human_speech(full_text)
        except asyncio.CancelledError:
            # More speech came in, debounce was reset
            pass

    def start_listening(self) -> None:
        """Enable listening for human speech.

        Call this before notifying the frontend to avoid race conditions
        where the user starts speaking before the pipeline is ready.
        """
        self._speech_event.clear()
        self._speech_complete_event.clear()
        self._speech_result = None
        self._accumulated_text = []
        if self._speech_debounce_task:
            self._speech_debounce_task.cancel()
            self._speech_debounce_task = None
        self._is_listening = True
        logger.debug("Listening enabled, ready for human speech")

    async def wait_for_human_speech(
        self,
        timeout_seconds: float = 60.0,
    ) -> HumanSpeechResult:
        """Wait for human to speak and return transcription.

        Note: Call start_listening() first to enable listening before
        notifying the frontend. This method will wait for speech to complete.

        Args:
            timeout_seconds: Maximum time to wait for speech

        Returns:
            HumanSpeechResult with transcribed text or timeout indication
        """
        # Ensure listening is enabled (in case called without start_listening)
        if not self._is_listening:
            self._speech_event.clear()
            self._speech_complete_event.clear()
            self._speech_result = None
            self._accumulated_text = []
            if self._speech_debounce_task:
                self._speech_debounce_task.cancel()
                self._speech_debounce_task = None
            self._is_listening = True

        logger.debug("Waiting for human speech (timeout: %ss)", timeout_seconds)

        try:
            # Wait for speech to complete (after debounce)
            await asyncio.wait_for(
                self._speech_complete_event.wait(),
                timeout=timeout_seconds,
            )
            return self._speech_result or HumanSpeechResult(
                text="",
                success=False,
            )
        except TimeoutError:
            # Cancel any pending debounce
            if self._speech_debounce_task:
                self._speech_debounce_task.cancel()
                self._speech_debounce_task = None

            # Check if we got any partial speech
            if self._accumulated_text:
                full_text = " ".join(self._accumulated_text)
                logger.debug("Timeout with accumulated speech: %s...", full_text[:100])
                return HumanSpeechResult(text=full_text, success=True, timed_out=True)
            return HumanSpeechResult(
                text="I have nothing to add at this time.",
                success=True,
                timed_out=True,
            )
        finally:
            # Stop listening when turn ends
            self._is_listening = False

    async def queue_ai_speech(
        self,
        text: str,
        voice_id: str | None = None,
        player_name: str | None = None,  # noqa: ARG002
    ) -> None:
        """Queue AI speech to be played to human.

        Args:
            text: Text to synthesize and play
            voice_id: Optional Cartesia voice ID (uses default if not provided)
            player_name: Name of the AI player speaking
        """
        if not self._tts or not self._task:
            return

        # Update voice if specified
        if voice_id:
            self._tts._voice_id = voice_id

        # Queue text for TTS
        frame = TextFrame(text)
        await self._task.queue_frame(frame)

    def on_human_speech(
        self,
        callback: Callable[[str], Awaitable[None]],
    ) -> None:
        """Register callback for when human finishes speaking."""
        self._on_human_speech = callback

    def on_interrupt(
        self,
        callback: Callable[[], Awaitable[None]],
    ) -> None:
        """Register callback for when human interrupts AI speech."""
        self._on_interrupt = callback


async def create_daily_room() -> tuple[str, str]:
    """Create a Daily room for voice communication.

    Returns:
        Tuple of (room_url, room_token)
    """
    import time

    import httpx

    async with httpx.AsyncClient() as client:
        # Create room
        response = await client.post(
            "https://api.daily.co/v1/rooms",
            headers={"Authorization": f"Bearer {settings.DAILY_API_KEY}"},
            json={
                "properties": {
                    "exp": int(time.time()) + 3600,  # 1 hour from now
                    "enable_chat": False,
                    "enable_screenshare": False,
                    "start_video_off": True,
                }
            },
        )
        response.raise_for_status()
        room_data = response.json()
        room_url = room_data["url"]
        room_name = room_data["name"]

        # Create token
        token_response = await client.post(
            "https://api.daily.co/v1/meeting-tokens",
            headers={"Authorization": f"Bearer {settings.DAILY_API_KEY}"},
            json={
                "properties": {
                    "room_name": room_name,
                    "is_owner": True,
                }
            },
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        room_token = token_data["token"]

        return room_url, room_token
