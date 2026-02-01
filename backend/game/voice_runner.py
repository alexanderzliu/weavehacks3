"""Voice-enabled game runner for human player participation.

This module extends the base GameRunner to support a human player
communicating via voice. AI players are unaware they're playing
with a human - the human's speech appears as normal text.
"""

from typing import Optional
from datetime import datetime

import weave

from game.runner import GameRunner, ROLE_DISTRIBUTION
from game.human_adapter import HumanPlayerAdapter
from game.llm import llm_client, LLMError
from game.tts import tts_client
from game.prompts import (
    SPEECH_SYSTEM_PROMPT,
    VOTE_SYSTEM_PROMPT,
    MAFIA_KILL_SYSTEM_PROMPT,
    DOCTOR_SAVE_SYSTEM_PROMPT,
    DEPUTY_INVESTIGATE_SYSTEM_PROMPT,
)
from models.schemas import (
    EventType,
    Visibility,
    ActorSpeech,
    ActorVote,
    ActorNightChoice,
)
from db.database import get_db_session
from db import crud


class VoiceGameRunner(GameRunner):
    """Game runner that supports a human player via voice.

    Extends the base GameRunner with:
    - Detection of human player in the game
    - Routing human turns to HumanPlayerAdapter instead of LLM
    - Streaming AI speech to human player
    - Handling human voting and night actions via UI
    """

    def __init__(
        self,
        game_id: str,
        series_id: str,
        human_adapter: Optional[HumanPlayerAdapter] = None,
        random_seed: Optional[int] = None,
    ):
        super().__init__(game_id, series_id, random_seed)
        self._human_adapter = human_adapter
        self._human_player_id: Optional[str] = None

    async def _load_game_players(self) -> list[dict]:
        """Load game players and identify the human player."""
        players = await super()._load_game_players()

        # Find human player if adapter is set
        if self._human_adapter:
            for player in self._game_players:
                if player.get("is_human"):
                    self._human_player_id = player["player_id"]
                    break

        return players

    def _is_human_player(self, player: dict) -> bool:
        """Check if a player is the human player."""
        return (
            self._human_adapter is not None
            and player.get("is_human", False)
        )

    @weave.op()
    async def _player_speech(self, player: dict) -> None:
        """Have a player give a speech - routes to human or AI."""
        if self._is_human_player(player):
            await self._human_player_speech(player)
        else:
            # AI player speech - also stream to human if present
            await self._ai_player_speech(player)

    async def _human_player_speech(self, player: dict) -> None:
        """Handle human player's speech turn."""
        context = self._build_game_context(player)

        # Get speech from human via adapter
        speech = await self._human_adapter.get_speech(context)
        content = speech.content

        # Record in discussion (same as AI)
        self._day_discussion.append(f"{player['name']}: {content}")

        # Emit speech event (no TTS needed - human spoke directly)
        payload = {"content": content, "player_name": player["name"]}

        await self._emit_event(
            EventType.SPEECH,
            Visibility.PUBLIC,
            actor_id=player["player_id"],
            payload=payload,
        )

    async def _ai_player_speech(self, player: dict) -> None:
        """Handle AI player's speech turn (with streaming to human)."""
        context = self._build_game_context(player)
        system_prompt = SPEECH_SYSTEM_PROMPT.format(
            player_name=player["name"],
            game_context=context,
        )

        try:
            speech = await llm_client.complete_json(
                provider=player["model_provider"],
                model_name=player["model_name"],
                system_prompt=system_prompt,
                user_prompt="Give your speech now.",
                response_model=ActorSpeech,
            )
            content = speech.content
        except LLMError as e:
            print(f"LLM ERROR (_player_speech) for {player['name']}: {e}")
            content = "I have nothing to add at this time."

        # Stream speech to human player if connected
        if self._human_adapter:
            await self._human_adapter.stream_ai_speech(player["name"], content)

        # Generate TTS audio for other viewers
        audio_base64 = await tts_client.generate_speech(content, player["name"])

        # Record in discussion
        self._day_discussion.append(f"{player['name']}: {content}")

        # Build payload with optional audio
        payload = {"content": content, "player_name": player["name"]}
        if audio_base64:
            payload["audio_base64"] = audio_base64

        await self._emit_event(
            EventType.SPEECH,
            Visibility.PUBLIC,
            actor_id=player["player_id"],
            payload=payload,
        )

    @weave.op()
    async def _player_vote(self, player: dict) -> str:
        """Have a player cast their vote - routes to human or AI."""
        if self._is_human_player(player):
            return await self._human_player_vote(player)
        else:
            return await super()._player_vote(player)

    async def _human_player_vote(self, player: dict) -> str:
        """Handle human player's vote."""
        alive_names = [
            p["name"] for p in self._get_alive_players()
            if p["player_id"] != player["player_id"]
        ]

        # Get vote from human via adapter (UI-based)
        vote_result = await self._human_adapter.get_vote(alive_names + ["no_lynch"])
        vote = vote_result.vote
        reasoning = vote_result.reasoning

        # Validate vote
        if vote != "no_lynch":
            target = self._get_player_by_name(vote)
            if not target or not target["is_alive"] or target["player_id"] == player["player_id"]:
                vote = "no_lynch"

        target_id = None
        if vote != "no_lynch":
            target = self._get_player_by_name(vote)
            if target:
                target_id = target["player_id"]

        await self._emit_event(
            EventType.VOTE_CAST,
            Visibility.PUBLIC,
            actor_id=player["player_id"],
            target_id=target_id,
            payload={
                "vote": vote,
                "reasoning": reasoning,
                "voter_name": player["name"],
                "target_name": vote,
            },
        )

        return vote

    @weave.op()
    async def _mafia_kill_choice(self) -> Optional[str]:
        """Get mafia's kill target - routes to human if mafia."""
        mafia_players = [p for p in self._get_alive_players() if p["role"] == "mafia"]
        if not mafia_players:
            return None

        # Use first alive mafia - check if human
        player = mafia_players[0]

        if self._is_human_player(player):
            return await self._human_mafia_kill(player)
        else:
            return await super()._mafia_kill_choice()

    async def _human_mafia_kill(self, player: dict) -> Optional[str]:
        """Handle human mafia player's kill choice."""
        valid_targets = [
            p["name"] for p in self._get_alive_players()
            if p["role"] != "mafia"
        ]

        if not valid_targets:
            return None

        # Get choice from human via adapter (UI-based)
        result = await self._human_adapter.get_night_action(valid_targets, "mafia")
        target = result.target

        # Validate
        if target not in valid_targets:
            target = valid_targets[0]

        target_player = self._get_player_by_name(target)
        await self._emit_event(
            EventType.MAFIA_KILL,
            Visibility.MAFIA,
            actor_id=player["player_id"],
            target_id=target_player["player_id"] if target_player else None,
            payload={"target": target, "reasoning": "Human player choice"},
        )

        return target

    @weave.op()
    async def _doctor_save_choice(self) -> Optional[str]:
        """Get doctor's save target - routes to human if doctor."""
        doctors = [p for p in self._get_alive_players() if p["role"] == "doctor"]
        if not doctors:
            return None

        player = doctors[0]

        if self._is_human_player(player):
            return await self._human_doctor_save(player)
        else:
            return await super()._doctor_save_choice()

    async def _human_doctor_save(self, player: dict) -> Optional[str]:
        """Handle human doctor player's save choice."""
        valid_targets = [p["name"] for p in self._get_alive_players()]

        # Get choice from human via adapter (UI-based)
        result = await self._human_adapter.get_night_action(valid_targets, "doctor")
        target = result.target

        # Validate
        if target not in valid_targets:
            target = valid_targets[0]

        target_player = self._get_player_by_name(target)
        await self._emit_event(
            EventType.DOCTOR_SAVE,
            Visibility.PRIVATE,
            actor_id=player["player_id"],
            target_id=target_player["player_id"] if target_player else None,
            payload={"target": target, "reasoning": "Human player choice"},
        )

        return target

    @weave.op()
    async def _deputy_investigate_choice(self) -> Optional[str]:
        """Get deputy's investigation target - routes to human if deputy."""
        deputies = [p for p in self._get_alive_players() if p["role"] == "deputy"]
        if not deputies:
            return None

        player = deputies[0]

        if self._is_human_player(player):
            return await self._human_deputy_investigate(player)
        else:
            return await super()._deputy_investigate_choice()

    async def _human_deputy_investigate(self, player: dict) -> Optional[str]:
        """Handle human deputy player's investigation choice."""
        valid_targets = [
            p["name"] for p in self._get_alive_players()
            if p["player_id"] != player["player_id"]
        ]

        if not valid_targets:
            return None

        # Get choice from human via adapter (UI-based)
        result = await self._human_adapter.get_night_action(valid_targets, "deputy")
        target = result.target

        # Validate
        if target not in valid_targets:
            target = valid_targets[0]

        target_player = self._get_player_by_name(target)
        is_mafia = target_player["role"] == "mafia" if target_player else False

        await self._emit_event(
            EventType.DEPUTY_INVESTIGATE,
            Visibility.PRIVATE,
            actor_id=player["player_id"],
            target_id=target_player["player_id"] if target_player else None,
            payload={
                "target": target,
                "result": "bad" if is_mafia else "good",
                "reasoning": "Human player choice",
            },
        )

        return target
