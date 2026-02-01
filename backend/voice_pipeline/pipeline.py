"""Pipecat voice pipeline for human player in Mafia game.

This module provides real-time voice communication between a human player
and the game. It uses:
- Daily.co for WebRTC transport
- Deepgram for speech-to-text
- Cartesia for text-to-speech (AI player voices)
- Silero VAD for voice activity detection
"""

import asyncio
from typing import Callable, Optional, Awaitable
from dataclasses import dataclass

from pipecat.frames.frames import (
    Frame,
    TextFrame,
    TranscriptionFrame,
    EndFrame,
    TTSAudioRawFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.transports.daily.transport import DailyTransport, DailyParams
from pipecat.audio.vad.silero import SileroVADAnalyzer

from config import get_settings

settings = get_settings()


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
        on_speech_start: Optional[Callable[[], Awaitable[None]]] = None,
    ):
        super().__init__()
        self._on_transcription = on_transcription
        self._on_speech_start = on_speech_start
        self._current_transcript = ""
        self._is_speaking = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            # Final transcription received
            if frame.text:
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

        self._pipeline: Optional[Pipeline] = None
        self._task: Optional[PipelineTask] = None
        self._runner: Optional[PipelineRunner] = None
        self._transport: Optional[DailyTransport] = None
        self._tts: Optional[CartesiaTTSService] = None

        # Speech waiting
        self._speech_event = asyncio.Event()
        self._speech_result: Optional[HumanSpeechResult] = None

        # Callbacks
        self._on_human_speech: Optional[Callable[[str], Awaitable[None]]] = None
        self._on_interrupt: Optional[Callable[[], Awaitable[None]]] = None

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
        self._pipeline = Pipeline([
            self._transport.input(),
            stt,
            collector,
        ])

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
        """Handle completed transcription from human."""
        self._speech_result = HumanSpeechResult(text=text, success=True)
        self._speech_event.set()

        if self._on_human_speech:
            await self._on_human_speech(text)

    async def wait_for_human_speech(
        self,
        timeout_seconds: float = 60.0,
    ) -> HumanSpeechResult:
        """Wait for human to speak and return transcription.

        Args:
            timeout_seconds: Maximum time to wait for speech

        Returns:
            HumanSpeechResult with transcribed text or timeout indication
        """
        self._speech_event.clear()
        self._speech_result = None

        try:
            await asyncio.wait_for(
                self._speech_event.wait(),
                timeout=timeout_seconds,
            )
            return self._speech_result or HumanSpeechResult(
                text="",
                success=False,
            )
        except asyncio.TimeoutError:
            return HumanSpeechResult(
                text="I have nothing to add at this time.",
                success=True,
                timed_out=True,
            )

    async def queue_ai_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        player_name: Optional[str] = None,
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
    import httpx
    import time

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
