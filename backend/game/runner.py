"""Game runner - executes a single Mafia game."""
import random
from datetime import datetime
from typing import Optional
from uuid import uuid4

import weave

from db.database import get_db_session
from db import crud
from db.models import GamePlayer
from game.llm import llm_client, LLMError
from game.prompts import (
    GAME_CONTEXT_TEMPLATE,
    ROLE_INFO,
    SPEECH_SYSTEM_PROMPT,
    VOTE_SYSTEM_PROMPT,
    MAFIA_KILL_SYSTEM_PROMPT,
    DOCTOR_SAVE_SYSTEM_PROMPT,
    DEPUTY_INVESTIGATE_SYSTEM_PROMPT,
)
from models.schemas import (
    GameEvent,
    EventType,
    Visibility,
    GamePhase,
    Winner,
    Role,
    ActorSpeech,
    ActorVote,
    ActorNightChoice,
    ModelProvider,
    Cheatsheet,
)
from websocket.manager import ws_manager


# Role distribution per player count
ROLE_DISTRIBUTION = {
    5: {"mafia": 1, "doctor": 1, "deputy": 1, "townsperson": 2},
    6: {"mafia": 2, "doctor": 1, "deputy": 1, "townsperson": 2},
    7: {"mafia": 2, "doctor": 1, "deputy": 1, "townsperson": 3},
}


class GameRunner:
    """Runs a single game of Mafia."""

    def __init__(self, game_id: str, series_id: str, random_seed: Optional[int] = None):
        self.game_id = game_id
        self.series_id = series_id
        self.random = random.Random(random_seed)
        self._game_players: list[dict] = []  # Cached player data
        self._day_discussion: list[str] = []  # Current day's speeches
        self._day_number = 0

    async def _emit_event(
        self,
        event_type: EventType,
        visibility: Visibility,
        actor_id: Optional[str] = None,
        target_id: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> GameEvent:
        """Create, persist, and broadcast a game event."""
        event = GameEvent(
            id=str(uuid4()),
            ts=datetime.utcnow(),
            series_id=self.series_id,
            game_id=self.game_id,
            type=event_type,
            visibility=visibility,
            actor_id=actor_id,
            target_id=target_id,
            payload=payload or {},
        )

        async with get_db_session() as db:
            await crud.create_game_event(db, event)

        await ws_manager.broadcast_event(self.series_id, event)
        return event

    async def _load_game_players(self) -> list[dict]:
        """Load game players with their data."""
        async with get_db_session() as db:
            gps = await crud.get_game_players(db, self.game_id)
            self._game_players = []
            for gp in gps:
                # Load cheatsheet
                cheatsheet = await crud.get_latest_cheatsheet(db, gp.player.id)
                cs_schema = Cheatsheet(
                    items=[],
                    version=cheatsheet.version if cheatsheet else 0,
                )
                if cheatsheet and cheatsheet.items:
                    from models.schemas import CheatsheetItem
                    cs_schema.items = [CheatsheetItem.model_validate(i) for i in cheatsheet.items]

                self._game_players.append({
                    "game_player_id": gp.id,
                    "player_id": gp.player.id,
                    "name": gp.player.name,
                    "role": gp.role,
                    "is_alive": gp.is_alive,
                    "model_provider": ModelProvider(gp.player.model_provider),
                    "model_name": gp.player.model_name,
                    "cheatsheet": cs_schema,
                })
        return self._game_players

    def _get_alive_players(self) -> list[dict]:
        return [p for p in self._game_players if p["is_alive"]]

    def _get_dead_players(self) -> list[dict]:
        return [p for p in self._game_players if not p["is_alive"]]

    def _get_player_by_name(self, name: str) -> Optional[dict]:
        for p in self._game_players:
            if p["name"].lower() == name.lower():
                return p
        return None

    def _get_player_by_id(self, player_id: str) -> Optional[dict]:
        for p in self._game_players:
            if p["player_id"] == player_id:
                return p
        return None

    def _build_game_context(self, player: dict) -> str:
        """Build the game context string for a player."""
        alive = [p["name"] for p in self._get_alive_players()]
        dead = [p["name"] for p in self._get_dead_players()]

        role_info = ROLE_INFO.get(player["role"], "")
        if player["role"] == "mafia":
            partners = [p["name"] for p in self._game_players
                       if p["role"] == "mafia" and p["player_id"] != player["player_id"]]
            role_info = role_info.format(mafia_partners=", ".join(partners) if partners else "none (you're alone)")

        return GAME_CONTEXT_TEMPLATE.format(
            num_players=len(self._game_players),
            day_number=self._day_number,
            alive_players=", ".join(alive),
            dead_players=", ".join(dead) if dead else "none",
            player_name=player["name"],
            role=player["role"],
            role_info=role_info,
            cheatsheet=player["cheatsheet"].to_prompt_format(),
            discussion="\n".join(self._day_discussion) if self._day_discussion else "(No discussion yet)",
        )

    def _check_win_condition(self) -> Optional[Winner]:
        """Check if the game has ended."""
        alive = self._get_alive_players()
        mafia_count = sum(1 for p in alive if p["role"] == "mafia")
        town_count = len(alive) - mafia_count

        if mafia_count == 0:
            return Winner.TOWN
        if mafia_count >= town_count:
            return Winner.MAFIA
        return None

    @weave.op()
    async def run(self) -> Winner:
        """Run the game to completion."""
        await self._load_game_players()

        # Start game
        async with get_db_session() as db:
            await crud.update_game(db, self.game_id, status=GamePhase.DAY, started_at=datetime.utcnow())

        await self._emit_event(
            EventType.GAME_STARTED,
            Visibility.PUBLIC,
            payload={"player_count": len(self._game_players)},
        )

        # Game loop
        while True:
            self._day_number += 1

            # Day phase
            winner = await self._run_day_phase()
            if winner:
                break

            # Night phase
            winner = await self._run_night_phase()
            if winner:
                break

        # End game
        async with get_db_session() as db:
            await crud.update_game(
                db, self.game_id,
                status=GamePhase.COMPLETED,
                winner=winner.value,
                completed_at=datetime.utcnow(),
            )

        await self._emit_event(
            EventType.GAME_ENDED,
            Visibility.PUBLIC,
            payload={"winner": winner.value, "day_number": self._day_number},
        )

        return winner

    async def _run_day_phase(self) -> Optional[Winner]:
        """Run the day phase: speeches, voting, and lynch."""
        async with get_db_session() as db:
            await crud.update_game(db, self.game_id, status=GamePhase.DAY, day_number=self._day_number)

        await self._emit_event(
            EventType.DAY_STARTED,
            Visibility.PUBLIC,
            payload={"day_number": self._day_number},
        )

        # Broadcast snapshot (use names for frontend compatibility)
        alive = self._get_alive_players()
        await ws_manager.broadcast_snapshot(
            self.series_id,
            self.game_id,
            [p["name"] for p in alive],
            "day",
            self._day_number,
        )

        # Reset day discussion
        self._day_discussion = []

        # Shuffle speaking order
        speaking_order = alive.copy()
        self.random.shuffle(speaking_order)

        # Each alive player speaks once
        for player in speaking_order:
            await self._player_speech(player)

        # Voting phase
        async with get_db_session() as db:
            await crud.update_game(db, self.game_id, status=GamePhase.VOTING)

        votes = {}
        for player in alive:
            vote = await self._player_vote(player)
            votes[player["player_id"]] = vote

        # Resolve lynch
        lynched_player = await self._resolve_lynch(votes)

        # Check win condition
        return self._check_win_condition()

    @weave.op()
    async def _player_speech(self, player: dict) -> None:
        """Have a player give a speech."""
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
        except LLMError:
            content = "I have nothing to add at this time."

        # Record in discussion
        self._day_discussion.append(f"{player['name']}: {content}")

        await self._emit_event(
            EventType.SPEECH,
            Visibility.PUBLIC,
            actor_id=player["player_id"],
            payload={"content": content, "player_name": player["name"]},
        )

    @weave.op()
    async def _player_vote(self, player: dict) -> str:
        """Have a player cast their vote."""
        context = self._build_game_context(player)
        system_prompt = VOTE_SYSTEM_PROMPT.format(
            player_name=player["name"],
            game_context=context,
        )

        alive_names = [p["name"] for p in self._get_alive_players() if p["player_id"] != player["player_id"]]

        try:
            vote_result = await llm_client.complete_json(
                provider=player["model_provider"],
                model_name=player["model_name"],
                system_prompt=system_prompt,
                user_prompt=f"Cast your vote. Valid targets: {', '.join(alive_names)}, or 'no_lynch'",
                response_model=ActorVote,
            )
            vote = vote_result.vote
            reasoning = vote_result.reasoning

            # Validate vote
            if vote != "no_lynch":
                target = self._get_player_by_name(vote)
                if not target or not target["is_alive"] or target["player_id"] == player["player_id"]:
                    vote = self.random.choice(alive_names + ["no_lynch"])
        except LLMError:
            vote = self.random.choice(alive_names + ["no_lynch"])
            reasoning = "fallback"

        target_id = None
        if vote != "no_lynch":
            target = self._get_player_by_name(vote)
            if target:
                target_id = target["player_id"]

        target_name = vote if vote == "no_lynch" else vote
        await self._emit_event(
            EventType.VOTE_CAST,
            Visibility.PUBLIC,
            actor_id=player["player_id"],
            target_id=target_id,
            payload={
                "vote": vote,
                "reasoning": reasoning,
                "voter_name": player["name"],
                "target_name": target_name,
            },
        )

        return vote

    async def _resolve_lynch(self, votes: dict[str, str]) -> Optional[dict]:
        """Resolve voting and potentially lynch a player."""
        # Count votes
        vote_counts: dict[str, int] = {}
        for voter_id, vote in votes.items():
            vote_counts[vote] = vote_counts.get(vote, 0) + 1

        # Find plurality
        max_votes = max(vote_counts.values())
        top_voted = [name for name, count in vote_counts.items() if count == max_votes]

        lynched_player = None
        if len(top_voted) == 1 and top_voted[0] != "no_lynch":
            # Lynch the player
            target = self._get_player_by_name(top_voted[0])
            if target:
                lynched_player = target
                target["is_alive"] = False

                async with get_db_session() as db:
                    await crud.update_game_player(
                        db, target["game_player_id"],
                        is_alive=False,
                        eliminated_day=self._day_number,
                        elimination_type="lynched",
                    )

        await self._emit_event(
            EventType.LYNCH_RESULT,
            Visibility.PUBLIC,
            target_id=lynched_player["player_id"] if lynched_player else None,
            payload={
                "vote_counts": vote_counts,
                "lynched": lynched_player["name"] if lynched_player else None,
                "lynched_role": lynched_player["role"] if lynched_player else None,
                "lynched_player_name": lynched_player["name"] if lynched_player else None,
                "role": lynched_player["role"] if lynched_player else None,
            },
        )

        # Send updated snapshot after lynch
        if lynched_player:
            alive = self._get_alive_players()
            await ws_manager.broadcast_snapshot(
                self.series_id,
                self.game_id,
                [p["name"] for p in alive],
                "day",
                self._day_number,
            )

        return lynched_player

    async def _run_night_phase(self) -> Optional[Winner]:
        """Run the night phase: mafia kill, doctor save, deputy investigate."""
        async with get_db_session() as db:
            await crud.update_game(db, self.game_id, status=GamePhase.NIGHT)

        await self._emit_event(
            EventType.NIGHT_STARTED,
            Visibility.PUBLIC,
            payload={"day_number": self._day_number},
        )

        # Broadcast snapshot (use names for frontend compatibility)
        alive = self._get_alive_players()
        await ws_manager.broadcast_snapshot(
            self.series_id,
            self.game_id,
            [p["name"] for p in alive],
            "night",
            self._day_number,
        )

        # Get night actions
        mafia_target = await self._mafia_kill_choice()
        doctor_target = await self._doctor_save_choice()
        deputy_target = await self._deputy_investigate_choice()

        # Resolve night
        killed_player = None
        if mafia_target and mafia_target != doctor_target:
            target = self._get_player_by_name(mafia_target)
            if target and target["is_alive"]:
                killed_player = target
                target["is_alive"] = False

                async with get_db_session() as db:
                    await crud.update_game_player(
                        db, target["game_player_id"],
                        is_alive=False,
                        eliminated_day=self._day_number,
                        elimination_type="killed",
                    )

        await self._emit_event(
            EventType.NIGHT_RESULT,
            Visibility.PUBLIC,
            target_id=killed_player["player_id"] if killed_player else None,
            payload={
                "killed": killed_player["name"] if killed_player else None,
                "killed_role": killed_player["role"] if killed_player else None,
                "was_saved": mafia_target == doctor_target and mafia_target is not None,
                "killed_player_name": killed_player["name"] if killed_player else None,
            },
        )

        # Send updated snapshot after night kill
        if killed_player:
            alive = self._get_alive_players()
            await ws_manager.broadcast_snapshot(
                self.series_id,
                self.game_id,
                [p["name"] for p in alive],
                "night",
                self._day_number,
            )

        return self._check_win_condition()

    @weave.op()
    async def _mafia_kill_choice(self) -> Optional[str]:
        """Get mafia's kill target."""
        mafia_players = [p for p in self._get_alive_players() if p["role"] == "mafia"]
        if not mafia_players:
            return None

        # Use first alive mafia member to make decision (includes partner info in context)
        player = mafia_players[0]
        context = self._build_game_context(player)
        system_prompt = MAFIA_KILL_SYSTEM_PROMPT.format(
            player_name=player["name"],
            game_context=context,
        )

        valid_targets = [p["name"] for p in self._get_alive_players() if p["role"] != "mafia"]

        try:
            result = await llm_client.complete_json(
                provider=player["model_provider"],
                model_name=player["model_name"],
                system_prompt=system_prompt,
                user_prompt=f"Choose your target. Valid targets: {', '.join(valid_targets)}",
                response_model=ActorNightChoice,
            )
            target = result.target
            reasoning = result.reasoning

            # Validate
            if target not in valid_targets:
                target = self.random.choice(valid_targets) if valid_targets else None
        except LLMError:
            target = self.random.choice(valid_targets) if valid_targets else None
            reasoning = "fallback"

        if target:
            target_player = self._get_player_by_name(target)
            await self._emit_event(
                EventType.MAFIA_KILL,
                Visibility.MAFIA,
                actor_id=player["player_id"],
                target_id=target_player["player_id"] if target_player else None,
                payload={"target": target, "reasoning": reasoning},
            )

        return target

    @weave.op()
    async def _doctor_save_choice(self) -> Optional[str]:
        """Get doctor's save target."""
        doctors = [p for p in self._get_alive_players() if p["role"] == "doctor"]
        if not doctors:
            return None

        player = doctors[0]
        context = self._build_game_context(player)
        system_prompt = DOCTOR_SAVE_SYSTEM_PROMPT.format(
            player_name=player["name"],
            game_context=context,
        )

        valid_targets = [p["name"] for p in self._get_alive_players()]

        try:
            result = await llm_client.complete_json(
                provider=player["model_provider"],
                model_name=player["model_name"],
                system_prompt=system_prompt,
                user_prompt=f"Choose who to protect. Valid targets: {', '.join(valid_targets)}",
                response_model=ActorNightChoice,
            )
            target = result.target
            reasoning = result.reasoning

            if target not in valid_targets:
                target = self.random.choice(valid_targets)
        except LLMError:
            target = self.random.choice(valid_targets)
            reasoning = "fallback"

        target_player = self._get_player_by_name(target)
        await self._emit_event(
            EventType.DOCTOR_SAVE,
            Visibility.PRIVATE,
            actor_id=player["player_id"],
            target_id=target_player["player_id"] if target_player else None,
            payload={"target": target, "reasoning": reasoning},
        )

        return target

    @weave.op()
    async def _deputy_investigate_choice(self) -> Optional[str]:
        """Get deputy's investigation target and reveal result."""
        deputies = [p for p in self._get_alive_players() if p["role"] == "deputy"]
        if not deputies:
            return None

        player = deputies[0]
        context = self._build_game_context(player)
        system_prompt = DEPUTY_INVESTIGATE_SYSTEM_PROMPT.format(
            player_name=player["name"],
            game_context=context,
        )

        valid_targets = [p["name"] for p in self._get_alive_players() if p["player_id"] != player["player_id"]]

        try:
            result = await llm_client.complete_json(
                provider=player["model_provider"],
                model_name=player["model_name"],
                system_prompt=system_prompt,
                user_prompt=f"Choose who to investigate. Valid targets: {', '.join(valid_targets)}",
                response_model=ActorNightChoice,
            )
            target = result.target
            reasoning = result.reasoning

            if target not in valid_targets:
                target = self.random.choice(valid_targets) if valid_targets else None
        except LLMError:
            target = self.random.choice(valid_targets) if valid_targets else None
            reasoning = "fallback"

        if target:
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
                    "reasoning": reasoning,
                },
            )

        return target


async def assign_roles(game_id: str, player_ids: list[str], random_seed: Optional[int] = None) -> None:
    """Assign roles to players for a game."""
    rng = random.Random(random_seed)
    num_players = len(player_ids)

    if num_players not in ROLE_DISTRIBUTION:
        raise ValueError(f"Unsupported player count: {num_players}")

    distribution = ROLE_DISTRIBUTION[num_players]
    roles = []
    for role, count in distribution.items():
        roles.extend([role] * count)

    rng.shuffle(roles)
    rng.shuffle(player_ids)

    async with get_db_session() as db:
        for player_id, role in zip(player_ids, roles):
            await crud.create_game_player(db, game_id, player_id, role)
