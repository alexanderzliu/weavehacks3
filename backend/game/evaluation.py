"""Weave evaluation for cheatsheet helpfulness.

Evaluates whether a player's cheatsheet helped them perform well in a Mafia game.
Uses LLM-as-judge to score across multiple dimensions:
- Team victory contribution
- Survival contribution
- Decision quality (role-specific)
- Overall cheatsheet helpfulness
"""
from typing import Any, Optional

import weave
from pydantic import BaseModel, Field

from db.database import get_db_session
from db import crud
from game.llm import llm_client
from models.schemas import ModelProvider, Cheatsheet, CheatsheetItem


# ============ Data Models ============


class ScorerOutput(BaseModel):
    """Structured output from the LLM scorer."""

    team_victory_contribution: float = Field(
        ge=0.0, le=1.0, description="How much did the cheatsheet help the team win?"
    )
    survival_contribution: float = Field(
        ge=0.0, le=1.0, description="How much did the cheatsheet help the player survive?"
    )
    decision_quality: float = Field(
        ge=0.0, le=1.0, description="How good were the player's role-specific decisions?"
    )
    overall_score: float = Field(
        ge=0.0, le=1.0, description="Weighted composite score (40% victory, 20% survival, 40% decisions)"
    )
    explanation: str = Field(description="Detailed reasoning for the scores")


# ============ Scorer Prompt ============


SCORER_SYSTEM_PROMPT = """You are evaluating how helpful a player's cheatsheet was during a Mafia game.

PLAYER: {player_name}
ROLE: {role}
TEAM WON: {team_won}
PLAYER SURVIVED: {survived}

CHEATSHEET (version {cheatsheet_version}):
{cheatsheet_text}

GAME TRANSCRIPT:
{transcript}

PLAYER'S SPEECHES:
{speeches}

PLAYER'S VOTES:
{votes}

PLAYER'S NIGHT ACTIONS:
{night_actions}

Evaluate the cheatsheet's helpfulness across three dimensions:

1. **team_victory_contribution** (0.0-1.0): Did the cheatsheet contain strategies that helped the team win?
   - Consider role-appropriate tactics (deception for mafia, detection for town)
   - Look for evidence the player followed cheatsheet advice
   - 0.0 = no helpful content or actively harmful, 1.0 = directly contributed to victory

2. **survival_contribution** (0.0-1.0): Did the cheatsheet help the player survive longer?
   - Consider defensive strategies, threat assessment, alliance building
   - 0.0 = no survival tips or counterproductive, 1.0 = directly aided survival

3. **decision_quality** (0.0-1.0): How well did the player's decisions align with good play for their role?
   Role-specific criteria:
   - MAFIA: Deception skill, misdirection, kill target selection, avoiding detection
   - DOCTOR: Protection of key town members, reading threats, self-preservation balance
   - DEPUTY: Investigation targeting, information sharing timing
   - TOWNSPERSON: Deduction accuracy, voting rationale, information gathering

4. **overall_score** (0.0-1.0): Calculate as weighted composite:
   - team_victory_contribution * 0.40
   - survival_contribution * 0.20
   - decision_quality * 0.40

Focus on CAUSALITY: did the cheatsheet actually influence better play, or would the player have done the same thing without it? Look for specific instances where cheatsheet advice was applied (or ignored).

Respond with valid JSON only."""


# ============ Dataset Builder ============


async def build_evaluation_dataset(
    series_id: str,
    game_numbers: Optional[list[int]] = None,
) -> list[dict]:
    """Build evaluation dataset from completed games.

    Args:
        series_id: Series to evaluate
        game_numbers: Specific games to include (None = all completed)

    Returns:
        List of dicts suitable for Weave evaluation
    """
    rows = []

    async with get_db_session() as db:
        games = await crud.get_games_for_series(db, series_id)

        for game in games:
            # Skip incomplete games
            if game.status != "completed" or game.winner is None:
                continue

            # Filter by game_numbers if specified
            if game_numbers and game.game_number not in game_numbers:
                continue

            # Get game events for transcript
            events = await crud.get_game_events(db, game.id)
            transcript = _format_transcript(events)

            # Get all players in this game
            game_players = await crud.get_game_players(db, game.id)

            for gp in game_players:
                # Get cheatsheet that was used during this game
                cheatsheet_db = await crud.get_cheatsheet_at_game(
                    db, gp.player.id, game.game_number
                )

                if cheatsheet_db:
                    cs = Cheatsheet(
                        items=[
                            CheatsheetItem.model_validate(i)
                            for i in cheatsheet_db.items
                        ]
                        if cheatsheet_db.items
                        else [],
                        version=cheatsheet_db.version,
                    )
                    cheatsheet_text = cs.to_prompt_format()
                    cheatsheet_version = cs.version
                else:
                    cheatsheet_text = "No cheatsheet"
                    cheatsheet_version = 0

                # Determine if player's team won
                is_mafia = gp.role == "mafia"
                team_won = (is_mafia and game.winner == "mafia") or (
                    not is_mafia and game.winner == "town"
                )

                # Extract player's actions
                player_events = [
                    e for e in events if e.actor_player_id == gp.player.id
                ]
                speeches = [
                    e.payload.get("content", "")
                    for e in player_events
                    if e.type == "speech"
                ]
                votes = [
                    {
                        "target": e.payload.get("vote"),
                        "reasoning": e.payload.get("reasoning"),
                    }
                    for e in player_events
                    if e.type == "vote_cast"
                ]
                night_actions = [
                    {
                        "type": e.type,
                        "target": e.payload.get("target"),
                        "reasoning": e.payload.get("reasoning"),
                    }
                    for e in player_events
                    if e.type in ("mafia_kill", "doctor_save", "deputy_investigate")
                ]

                rows.append(
                    {
                        "game_id": game.id,
                        "game_number": game.game_number,
                        "player_id": gp.player.id,
                        "player_name": gp.player.name,
                        "role": gp.role,
                        "team_won": team_won,
                        "survived": gp.is_alive,
                        "cheatsheet_text": cheatsheet_text,
                        "cheatsheet_version": cheatsheet_version,
                        "transcript": transcript,
                        "speeches": speeches,
                        "votes": votes,
                        "night_actions": night_actions,
                    }
                )

    return rows


def _format_transcript(events: list) -> str:
    """Format game events into readable transcript."""
    lines = []
    for e in events:
        # Only include public events in transcript
        if e.visibility != "public":
            continue

        if e.type == "game_started":
            lines.append(f"[GAME START] {e.payload.get('player_count', '?')} players")
        elif e.type == "day_started":
            lines.append(f"\n=== DAY {e.payload.get('day_number', '?')} ===")
        elif e.type == "speech":
            name = e.payload.get("player_name", "Unknown")
            content = e.payload.get("content", "")
            lines.append(f"{name}: {content}")
        elif e.type == "vote_cast":
            voter = e.payload.get("voter_name", "Unknown")
            target = e.payload.get("target_name", "unknown")
            lines.append(f"[VOTE] {voter} -> {target}")
        elif e.type == "lynch_result":
            lynched = e.payload.get("lynched")
            if lynched:
                role = e.payload.get("lynched_role", "unknown")
                lines.append(f"[LYNCH] {lynched} was lynched (was {role})")
            else:
                lines.append("[LYNCH] No one was lynched")
        elif e.type == "night_started":
            lines.append(f"\n=== NIGHT {e.payload.get('day_number', '?')} ===")
        elif e.type == "night_result":
            killed = e.payload.get("killed")
            if killed:
                role = e.payload.get("killed_role", "unknown")
                lines.append(f"[KILLED] {killed} was killed (was {role})")
            elif e.payload.get("was_saved"):
                lines.append("[SAVED] Someone was saved by the doctor")
            else:
                lines.append("[NIGHT] No one was killed")
        elif e.type == "game_ended":
            lines.append(f"\n[GAME END] {e.payload.get('winner', 'unknown')} wins!")

    return "\n".join(lines)


# ============ Weave Model & Scorer ============


class CheatsheetModel(weave.Model):
    """Simple model that passes through cheatsheet data for evaluation."""

    @weave.op()
    async def predict(
        self,
        cheatsheet_text: str,
        cheatsheet_version: int,
        **kwargs: Any,
    ) -> dict:
        """Return cheatsheet data as the 'output' for scoring."""
        return {
            "cheatsheet_text": cheatsheet_text,
            "cheatsheet_version": cheatsheet_version,
        }


class CheatsheetScorer(weave.Scorer):
    """LLM-as-judge scorer for cheatsheet helpfulness."""

    model_provider: str = "openai"
    model_name: str = "gpt-5-mini"

    @weave.op()
    async def score(
        self,
        output: dict,
        player_name: str,
        role: str,
        team_won: bool,
        survived: bool,
        transcript: str,
        speeches: list[str],
        votes: list[dict],
        night_actions: list[dict],
    ) -> dict:
        """Score a cheatsheet based on game performance.

        Args:
            output: Model output containing cheatsheet_text and cheatsheet_version
            player_name: Name of the player
            role: Player's role in the game
            team_won: Whether the player's team won
            survived: Whether the player survived
            transcript: Full game transcript
            speeches: Player's speeches during the game
            votes: Player's voting history
            night_actions: Player's night actions

        Returns:
            Dictionary with scores and explanation
        """
        cheatsheet_text = output["cheatsheet_text"]
        cheatsheet_version = output["cheatsheet_version"]

        system_prompt = SCORER_SYSTEM_PROMPT.format(
            player_name=player_name,
            role=role,
            team_won="Yes" if team_won else "No",
            survived="Yes" if survived else "No",
            cheatsheet_version=cheatsheet_version,
            cheatsheet_text=cheatsheet_text,
            transcript=transcript,
            speeches="\n".join(speeches) if speeches else "(no speeches)",
            votes="\n".join(
                f"- Voted for {v['target']}: {v.get('reasoning', 'no reasoning')}"
                for v in votes
            )
            if votes
            else "(no votes)",
            night_actions="\n".join(
                f"- {a['type']}: targeted {a['target']} ({a.get('reasoning', 'no reasoning')})"
                for a in night_actions
            )
            if night_actions
            else "(no night actions)",
        )

        result = await llm_client.complete_json(
            provider=ModelProvider(self.model_provider),
            model_name=self.model_name,
            system_prompt=system_prompt,
            user_prompt="Evaluate the cheatsheet's helpfulness and provide scores.",
            response_model=ScorerOutput,
        )

        return {
            "overall_score": result.overall_score,
            "team_victory_contribution": result.team_victory_contribution,
            "survival_contribution": result.survival_contribution,
            "decision_quality": result.decision_quality,
            "explanation": result.explanation,
        }


# ============ Evaluation Runner ============


async def run_cheatsheet_evaluation(
    series_id: str,
    eval_name: Optional[str] = None,
    game_numbers: Optional[list[int]] = None,
    scorer_provider: str = "openai",
    scorer_model: str = "gpt-5-mini",
) -> dict:
    """Run cheatsheet evaluation on a series using Weave Evaluation.

    Args:
        series_id: Series to evaluate
        eval_name: Name for this evaluation run
        game_numbers: Specific games to evaluate (default: all completed)
        scorer_provider: LLM provider for scoring (anthropic/openai/google)
        scorer_model: Model name for scoring

    Returns:
        Evaluation results from Weave
    """
    # Build dataset
    rows = await build_evaluation_dataset(series_id, game_numbers)

    if not rows:
        return {"error": "No completed games found", "rows": 0}

    # Create scorer
    scorer = CheatsheetScorer(
        model_provider=scorer_provider,
        model_name=scorer_model,
    )

    # Create model
    model = CheatsheetModel()

    # Create Weave Evaluation
    evaluation = weave.Evaluation(
        dataset=rows,
        scorers=[scorer],
        name=eval_name or f"cheatsheet-eval-{series_id}",
    )

    # Run evaluation - this is properly traced as an Evaluation in Weave
    results = await evaluation.evaluate(model)

    return {
        "series_id": series_id,
        "total_rows": len(rows),
        "results": results,
    }


async def get_evaluation_summary(
    series_id: str,
    game_numbers: Optional[list[int]] = None,
) -> dict:
    """Get a quick summary without running full LLM evaluation.

    Useful for checking dataset size and basic stats before committing to LLM costs.
    """
    rows = await build_evaluation_dataset(series_id, game_numbers)

    if not rows:
        return {"error": "No completed games found", "rows": 0}

    # Basic stats
    total_rows = len(rows)
    games = set(r["game_number"] for r in rows)
    players = set(r["player_id"] for r in rows)
    wins = sum(1 for r in rows if r["team_won"])
    survivals = sum(1 for r in rows if r["survived"])

    # Cheatsheet stats
    has_cheatsheet = sum(1 for r in rows if r["cheatsheet_text"] != "No cheatsheet")
    avg_version = (
        sum(r["cheatsheet_version"] for r in rows) / total_rows if total_rows > 0 else 0
    )

    return {
        "series_id": series_id,
        "total_evaluation_rows": total_rows,
        "games_count": len(games),
        "games": sorted(games),
        "players_count": len(players),
        "win_rate": wins / total_rows if total_rows > 0 else 0,
        "survival_rate": survivals / total_rows if total_rows > 0 else 0,
        "rows_with_cheatsheet": has_cheatsheet,
        "avg_cheatsheet_version": avg_version,
        "estimated_llm_calls": total_rows,
    }
