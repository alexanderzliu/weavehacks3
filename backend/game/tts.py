"""Cartesia TTS client with lazy init and voice mapping."""

import base64
import logging

from cartesia import AsyncCartesia

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TTSError(Exception):
    """TTS generation failed."""

    pass


# Voice mapping: player name -> Cartesia voice ID
# Uses diverse voices from Cartesia's library
VOICE_MAP: dict[str, str] = {
    "Alice": "f786b574-daa5-4673-aa0c-cbe3e8534c02",  # Katie - Friendly Fixer
    "Bob": "5ee9feff-1265-424a-9d7f-8e4d431a12c7",  # Ronald - Thinker
    "Charlie": "79f8b5fb-2cc8-479a-80df-29f7a7cf1a3e",  # Theo - Modern Narrator
    "Diana": "f9836c6e-a0bd-460e-9d3c-f7299fa60f94",  # Caroline - Southern Guide
    "Eve": "a33f7a4c-100f-41cf-a1fd-5822e8fc253f",  # Lauren - Lively Narrator
    # Additional voices for custom player names
    "Frank": "87286a8d-7ea7-4235-a41a-dd9fa6630feb",  # Henry - Plainspoken Guy
    "Grace": "5c5ad5e7-1020-476b-8b91-fdcbe9cc313c",  # Daniela - Relaxed Woman
}
DEFAULT_VOICE_ID = "a167e0f3-df7e-4d52-a9c3-f949145efdab"  # Blake - Helpful Agent


class TTSClient:
    """Lazy-init async Cartesia TTS client.

    TTS is an optional enhancement - callers handle TTSError gracefully.
    """

    def __init__(self):
        self._client: AsyncCartesia | None = None

    def _get_client(self) -> AsyncCartesia:
        if self._client is None:
            self._client = AsyncCartesia(api_key=settings.CARTESIA_API_KEY)
        return self._client

    def is_configured(self) -> bool:
        """Check if TTS is configured (API key present)."""
        return bool(settings.CARTESIA_API_KEY)

    async def generate_speech(self, text: str, player_name: str) -> str:
        """Generate TTS audio, return base64 string.

        Raises:
            TTSError: If TTS is not configured or generation fails.
        """
        if not settings.CARTESIA_API_KEY:
            raise TTSError("CARTESIA_API_KEY not configured")

        voice_id = VOICE_MAP.get(player_name, DEFAULT_VOICE_ID)

        try:
            client = self._get_client()
            chunks: list[bytes] = []
            async for chunk in client.tts.bytes(
                model_id="sonic-2",
                transcript=text,
                voice={"mode": "id", "id": voice_id},
                output_format={
                    "container": "wav",
                    "sample_rate": 44100,
                    "encoding": "pcm_s16le",
                },
            ):
                chunks.append(chunk)

            audio_bytes = b"".join(chunks)
            return base64.b64encode(audio_bytes).decode("utf-8")
        except TTSError:
            raise
        except Exception as e:
            # Log at debug; caller (runner.py) handles user-visible logging
            logger.debug("TTS API error for %s: %s", player_name, e)
            raise TTSError(f"TTS generation failed: {e}") from e


# Global singleton
tts_client = TTSClient()
