"""Human player adapter for voice interaction in Mafia game.

This module bridges the Pipecat voice pipeline with the game runner,
allowing a human player to participate via voice while appearing as
a normal player to AI agents.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from game.tts import DEFAULT_VOICE_ID, VOICE_MAP
from models.schemas import ActorNightChoice, ActorSpeech, ActorVote


@dataclass
class HumanPlayerInfo:
    """Information about the human player."""

    player_id: str
    player_name: str
    role: str | None = None


class HumanPlayerAdapter:
    """Adapts human voice input to the game runner interface.

    This class:
    - Waits for human speech during their turn
    - Converts transcribed speech to ActorSpeech objects
    - Queues AI speeches to be played to the human
    - Handles voting and night actions (signaled to frontend)

    From the AI agents' perspective, the human is just another player
    whose speech text appears in the game context.
    """

    def __init__(
        self,
        player_id: str,
        player_name: str,
        ws_notify: Callable[[str, dict], Awaitable[None]],
    ):
        """Initialize the human player adapter.

        Args:
            player_id: Unique ID for the human player
            player_name: Display name for the human player
            ws_notify: Callback to send WebSocket messages to human's client
        """
        self.player_id = player_id
        self.player_name = player_name
        self._ws_notify = ws_notify

        # Voice pipeline (set when connected)
        self._pipeline = None

        # Speech waiting
        self._speech_event = asyncio.Event()
        self._speech_text: str | None = None
        self._speech_timeout = 60.0

        # Vote waiting
        self._vote_event = asyncio.Event()
        self._vote_choice: str | None = None

        # Night action waiting
        self._night_action_event = asyncio.Event()
        self._night_action_target: str | None = None

    def set_pipeline(self, pipeline) -> None:
        """Set the voice pipeline for audio I/O."""
        self._pipeline = pipeline
        if pipeline:
            pipeline.on_human_speech(self._on_speech_received)

    async def _on_speech_received(self, text: str) -> None:
        """Called when human speech is transcribed."""
        self._speech_text = text
        self._speech_event.set()

    def is_human_player(self, player_id: str) -> bool:
        """Check if the given player ID is the human player."""
        return player_id == self.player_id

    async def get_speech(self, game_context: str) -> ActorSpeech:  # noqa: ARG002
        """Get speech from the human player.

        This is called by the game runner when it's the human's turn to speak.
        It signals the frontend and waits for voice input.

        Args:
            game_context: Current game context (not shown to human, but kept for interface)

        Returns:
            ActorSpeech with the human's transcribed speech
        """
        # Reset state
        self._speech_event.clear()
        self._speech_text = None

        # Notify frontend that human should speak
        await self._ws_notify(
            "human_turn_start",
            {
                "player_id": self.player_id,
                "player_name": self.player_name,
                "action": "speech",
            },
        )

        # Wait for speech from pipeline or WebSocket
        if self._pipeline:
            result = await self._pipeline.wait_for_human_speech(self._speech_timeout)
            text = result.text
        else:
            # Fallback: wait for text via WebSocket
            try:
                await asyncio.wait_for(
                    self._speech_event.wait(),
                    timeout=self._speech_timeout,
                )
                text = self._speech_text or "I have nothing to add at this time."
            except TimeoutError:
                text = "I have nothing to add at this time."

        # Notify frontend that turn ended
        await self._ws_notify(
            "human_turn_end",
            {
                "player_id": self.player_id,
            },
        )

        return ActorSpeech(content=text, addressing=[])

    async def get_vote(self, valid_targets: list[str]) -> ActorVote:
        """Get vote from the human player via UI.

        Args:
            valid_targets: List of valid player names to vote for

        Returns:
            ActorVote with the human's choice
        """
        self._vote_event.clear()
        self._vote_choice = None

        # Notify frontend that human should vote
        await self._ws_notify(
            "human_vote_required",
            {
                "player_id": self.player_id,
                "player_name": self.player_name,
                "valid_targets": valid_targets,
            },
        )

        # Wait for vote via WebSocket
        try:
            await asyncio.wait_for(
                self._vote_event.wait(),
                timeout=self._speech_timeout,
            )
            vote = self._vote_choice or "no_lynch"
        except TimeoutError:
            vote = "no_lynch"

        return ActorVote(vote=vote, reasoning="Human player choice")

    async def get_night_action(self, valid_targets: list[str], role: str) -> ActorNightChoice:
        """Get night action from the human player via UI.

        Args:
            valid_targets: List of valid player names to target
            role: Human's role (mafia, doctor, deputy)

        Returns:
            ActorNightChoice with the human's target
        """
        self._night_action_event.clear()
        self._night_action_target = None

        # Notify frontend that human needs to take night action
        await self._ws_notify(
            "human_night_action_required",
            {
                "player_id": self.player_id,
                "player_name": self.player_name,
                "role": role,
                "valid_targets": valid_targets,
            },
        )

        # Wait for action via WebSocket
        try:
            await asyncio.wait_for(
                self._night_action_event.wait(),
                timeout=self._speech_timeout,
            )
            target = self._night_action_target or valid_targets[0]
        except TimeoutError:
            # Default to first valid target on timeout
            target = valid_targets[0] if valid_targets else ""

        return ActorNightChoice(target=target, reasoning="Human player choice")

    async def stream_ai_speech(self, player_name: str, content: str) -> None:
        """Stream AI player speech to the human via TTS.

        Args:
            player_name: Name of the AI player speaking
            content: Speech text to synthesize
        """
        if not self._pipeline:
            return

        # Get voice ID for this player
        voice_id = VOICE_MAP.get(player_name, DEFAULT_VOICE_ID)

        # Queue speech for TTS playback
        await self._pipeline.queue_ai_speech(
            text=content,
            voice_id=voice_id,
            player_name=player_name,
        )

    # Methods called by WebSocket handler when human sends input

    def receive_speech_text(self, text: str) -> None:
        """Receive speech text from WebSocket (fallback if no voice)."""
        self._speech_text = text
        self._speech_event.set()

    def receive_vote(self, vote: str) -> None:
        """Receive vote choice from WebSocket."""
        self._vote_choice = vote
        self._vote_event.set()

    def receive_night_action(self, target: str) -> None:
        """Receive night action target from WebSocket."""
        self._night_action_target = target
        self._night_action_event.set()
