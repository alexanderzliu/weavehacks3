"""Reflection pipeline - Reflector and Curator for cheatsheet evolution."""
from typing import Optional
from uuid import uuid4

import weave

from db.database import get_db_session
from db import crud
from game.llm import llm_client, LLMError
from models.schemas import (
    ModelProvider,
    Cheatsheet,
    CheatsheetItem,
    ReflectorOutput,
    CuratorOutput,
    DeltaUpdate,
    CuratorDecision,
    GameEvent,
    EventType,
    Visibility,
)
from websocket.manager import ws_manager


REFLECTOR_SYSTEM_PROMPT = """You are analyzing a completed Mafia game for player {player_name}.
Your job is to identify lessons learned and suggest updates to their strategy cheatsheet.

PLAYER'S ROLE THIS GAME: {role}
GAME OUTCOME: {outcome} ({winner} won)
PLAYER SURVIVED: {survived}

CURRENT CHEATSHEET:
{cheatsheet}

FULL GAME LOG (from viewer perspective):
{game_log}

Analyze the game and suggest cheatsheet updates. Consider:
1. What strategies worked well?
2. What mistakes were made?
3. What patterns did you notice in other players?
4. What should be remembered for future games?

Respond with JSON:
{{
  "player_id": "{player_id}",
  "game_analysis": "2-3 sentence analysis of the game from this player's perspective",
  "delta_updates": [
    {{
      "action": "add|update|remove",
      "item": {{"category": "...", "content": "...", "helpfulness_score": 0.5}},
      "item_id": "existing_item_id_for_update_or_remove",
      "reasoning": "why this change"
    }}
  ],
  "overall_assessment": "1 sentence on player's performance"
}}

Categories: "deception", "detection", "voting", "night_actions", "general"
Keep items concise (1-2 sentences). Suggest 0-3 updates per game."""


CURATOR_SYSTEM_PROMPT = """You are curating cheatsheet updates for player {player_name}.
Your job is to accept, reject, or merge proposed changes to maintain a high-quality, non-redundant cheatsheet.

CURRENT CHEATSHEET:
{cheatsheet}

PROPOSED UPDATES FROM REFLECTOR:
{reflector_output}

For each proposed delta, decide:
- "accept": Add/apply the change as-is
- "reject": Don't apply (not useful, redundant, or wrong)
- "merge": Combine with existing item (specify merge_with_id)

Also:
- Adjust helpfulness_score for existing items based on game performance (+/- 0.1)
- Flag items for pruning if score drops below 0.2

Respond with JSON:
{{
  "player_id": "{player_id}",
  "decisions": [
    {{
      "delta_index": 0,
      "decision": "accept|reject|merge",
      "reasoning": "why",
      "merge_with_id": "item_id if merging"
    }}
  ],
  "score_adjustments": [
    {{"item_id": "...", "new_score": 0.6, "reasoning": "why"}}
  ],
  "prune_items": [
    {{"item_id": "...", "reasoning": "why"}}
  ],
  "final_cheatsheet": {{
    "items": [...],
    "version": {new_version}
  }}
}}"""


class ReflectionPipeline:
    """Runs reflection after each game to update player cheatsheets."""

    def __init__(self, series_id: str, game_id: str, game_number: int):
        self.series_id = series_id
        self.game_id = game_id
        self.game_number = game_number

    async def _emit_event(
        self,
        event_type: EventType,
        visibility: Visibility,
        actor_id: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> None:
        """Emit a reflection event."""
        event = GameEvent(
            id=str(uuid4()),
            series_id=self.series_id,
            game_id=self.game_id,
            type=event_type,
            visibility=visibility,
            actor_id=actor_id,
            payload=payload or {},
        )

        async with get_db_session() as db:
            await crud.create_game_event(db, event)

        await ws_manager.broadcast_event(self.series_id, event)

    async def _get_game_log(self) -> str:
        """Get the full game log for reflection."""
        async with get_db_session() as db:
            events = await crud.get_game_events(db, self.game_id)

        lines = []
        for e in events:
            if e.type == "speech":
                lines.append(f"[DAY] {e.payload.get('content', '')}")
            elif e.type == "vote_cast":
                lines.append(f"[VOTE] Player voted for {e.payload.get('vote', 'unknown')}")
            elif e.type == "lynch_result":
                lynched = e.payload.get("lynched")
                if lynched:
                    role = e.payload.get("lynched_role", "unknown")
                    lines.append(f"[LYNCH] {lynched} was lynched (was {role})")
                else:
                    lines.append("[LYNCH] No one was lynched")
            elif e.type == "night_result":
                killed = e.payload.get("killed")
                if killed:
                    role = e.payload.get("killed_role", "unknown")
                    lines.append(f"[NIGHT] {killed} was killed (was {role})")
                elif e.payload.get("was_saved"):
                    lines.append("[NIGHT] Someone was saved by the doctor")
                else:
                    lines.append("[NIGHT] No one was killed")
            elif e.type == "game_ended":
                lines.append(f"[END] Game ended - {e.payload.get('winner', 'unknown')} wins")

        return "\n".join(lines) if lines else "No events recorded"

    @weave.op()
    async def run_for_player(
        self,
        player_id: str,
        player_name: str,
        role: str,
        survived: bool,
        winner: str,
        model_provider: ModelProvider,
        model_name: str,
    ) -> Optional[Cheatsheet]:
        """Run reflection pipeline for a single player."""
        await self._emit_event(
            EventType.REFLECTION_STARTED,
            Visibility.VIEWER,
            actor_id=player_id,
            payload={"player_name": player_name, "game_number": self.game_number},
        )

        # Get current cheatsheet
        async with get_db_session() as db:
            cs_db = await crud.get_latest_cheatsheet(db, player_id)

        current_cheatsheet = Cheatsheet(items=[], version=0)
        if cs_db:
            current_cheatsheet = Cheatsheet(
                items=[CheatsheetItem.model_validate(i) for i in cs_db.items] if cs_db.items else [],
                version=cs_db.version,
            )

        # Get game log
        game_log = await self._get_game_log()

        # Determine outcome
        player_won = (role == "mafia" and winner == "mafia") or (role != "mafia" and winner == "town")
        outcome = "won" if player_won else "lost"

        # Run reflector
        try:
            reflector_output = await self._run_reflector(
                player_id=player_id,
                player_name=player_name,
                role=role,
                outcome=outcome,
                winner=winner,
                survived=survived,
                current_cheatsheet=current_cheatsheet,
                game_log=game_log,
                model_provider=model_provider,
                model_name=model_name,
            )
        except LLMError:
            # Skip reflection on LLM failure
            await self._emit_event(
                EventType.REFLECTION_COMPLETED,
                Visibility.VIEWER,
                actor_id=player_id,
                payload={"status": "failed", "reason": "reflector_error"},
            )
            return None

        # Run curator
        try:
            final_cheatsheet = await self._run_curator(
                player_id=player_id,
                player_name=player_name,
                current_cheatsheet=current_cheatsheet,
                reflector_output=reflector_output,
                model_provider=model_provider,
                model_name=model_name,
            )
        except LLMError:
            # Keep current cheatsheet on curator failure
            final_cheatsheet = current_cheatsheet

        # Persist new version
        async with get_db_session() as db:
            await crud.create_cheatsheet_version(
                db,
                player_id,
                [item.model_dump() for item in final_cheatsheet.items],
                self.game_number,
            )

        await self._emit_event(
            EventType.REFLECTION_COMPLETED,
            Visibility.VIEWER,
            actor_id=player_id,
            payload={
                "status": "success",
                "new_version": current_cheatsheet.version + 1,
                "items_count": len(final_cheatsheet.items),
            },
        )

        await self._emit_event(
            EventType.CHEATSHEET_UPDATED,
            Visibility.PUBLIC,
            actor_id=player_id,
            payload={
                "player_name": player_name,
                "version": current_cheatsheet.version + 1,
                "items_count": len(final_cheatsheet.items),
            },
        )

        return final_cheatsheet

    @weave.op()
    async def _run_reflector(
        self,
        player_id: str,
        player_name: str,
        role: str,
        outcome: str,
        winner: str,
        survived: bool,
        current_cheatsheet: Cheatsheet,
        game_log: str,
        model_provider: ModelProvider,
        model_name: str,
    ) -> ReflectorOutput:
        """Run the reflector to generate delta updates."""
        system_prompt = REFLECTOR_SYSTEM_PROMPT.format(
            player_name=player_name,
            player_id=player_id,
            role=role,
            outcome=outcome,
            winner=winner,
            survived="Yes" if survived else "No",
            cheatsheet=current_cheatsheet.to_prompt_format(),
            game_log=game_log,
        )

        result = await llm_client.complete_json(
            provider=model_provider,
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt="Analyze the game and suggest cheatsheet updates.",
            response_model=ReflectorOutput,
        )

        return result

    @weave.op()
    async def _run_curator(
        self,
        player_id: str,
        player_name: str,
        current_cheatsheet: Cheatsheet,
        reflector_output: ReflectorOutput,
        model_provider: ModelProvider,
        model_name: str,
    ) -> Cheatsheet:
        """Run the curator to finalize cheatsheet updates."""
        new_version = current_cheatsheet.version + 1

        system_prompt = CURATOR_SYSTEM_PROMPT.format(
            player_name=player_name,
            player_id=player_id,
            cheatsheet=current_cheatsheet.to_prompt_format(),
            reflector_output=reflector_output.model_dump_json(indent=2),
            new_version=new_version,
        )

        result = await llm_client.complete_json(
            provider=model_provider,
            model_name=model_name,
            system_prompt=system_prompt,
            user_prompt="Review the proposed updates and produce the final cheatsheet.",
            response_model=CuratorOutput,
        )

        # Use the curator's final cheatsheet
        final = result.final_cheatsheet
        final.version = new_version
        return final
