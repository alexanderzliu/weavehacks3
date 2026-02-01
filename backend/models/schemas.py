from datetime import datetime
from enum import Enum
from typing import Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ============ Enums ============

class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


class Role(str, Enum):
    MAFIA = "mafia"
    DOCTOR = "doctor"
    DEPUTY = "deputy"
    TOWNSPERSON = "townsperson"


class GamePhase(str, Enum):
    PENDING = "pending"
    DAY = "day"
    VOTING = "voting"
    NIGHT = "night"
    COMPLETED = "completed"


class SeriesStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    STOP_REQUESTED = "stop_requested"
    COMPLETED = "completed"


class Winner(str, Enum):
    MAFIA = "mafia"
    TOWN = "town"


class Visibility(str, Enum):
    PUBLIC = "public"
    MAFIA = "mafia"
    PRIVATE = "private"
    VIEWER = "viewer"


class EventType(str, Enum):
    # Phase events
    GAME_STARTED = "game_started"
    PHASE_CHANGED = "phase_changed"
    DAY_STARTED = "day_started"
    NIGHT_STARTED = "night_started"
    GAME_ENDED = "game_ended"

    # Day events
    SPEECH = "speech"
    VOTE_CAST = "vote_cast"
    LYNCH_RESULT = "lynch_result"

    # Night events
    MAFIA_KILL = "mafia_kill"
    DOCTOR_SAVE = "doctor_save"
    DEPUTY_INVESTIGATE = "deputy_investigate"
    NIGHT_RESULT = "night_result"

    # Reflection events
    REFLECTION_STARTED = "reflection_started"
    REFLECTION_COMPLETED = "reflection_completed"
    CHEATSHEET_UPDATED = "cheatsheet_updated"

    # System events
    ERROR = "error"


# ============ Cheatsheet Models ============

class CheatsheetItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    category: str
    content: str
    helpfulness_score: float = Field(ge=0.0, le=1.0, default=0.5)
    times_used: int = 0
    added_after_game: Optional[int] = None
    last_updated_game: Optional[int] = None
    source_event: Optional[str] = None  # The game event that taught this lesson


class Cheatsheet(BaseModel):
    items: list[CheatsheetItem] = []
    version: int = 0

    def to_prompt_format(self, max_items: int = 10) -> str:
        """Format cheatsheet for inclusion in agent prompts."""
        if not self.items:
            return "No strategies accumulated yet."

        # Sort by helpfulness and take top N
        sorted_items = sorted(self.items, key=lambda x: -x.helpfulness_score)[:max_items]

        by_category: dict[str, list[CheatsheetItem]] = {}
        for item in sorted_items:
            if item.category not in by_category:
                by_category[item.category] = []
            by_category[item.category].append(item)

        lines = []
        for category, items in sorted(by_category.items()):
            lines.append(f"\n## {category}")
            for item in items:
                score_pct = int(item.helpfulness_score * 100)
                lines.append(f"- [{score_pct}%] {item.content}")

        return "\n".join(lines)


# ============ Player Models ============

class PlayerConfig(BaseModel):
    name: str
    model_provider: ModelProvider
    model_name: str
    initial_cheatsheet: Optional[Cheatsheet] = None


class PlayerState(BaseModel):
    id: str
    name: str
    model_provider: ModelProvider
    model_name: str
    role: Optional[Role] = None
    is_alive: bool = True


# ============ Game Configuration ============

class GameConfig(BaseModel):
    discussion_turns_per_day: int = Field(default=1, ge=1)  # 1 speech per player for hackathon
    allow_no_lynch: bool = True
    timeout_seconds: int = Field(default=60, ge=10)
    random_seed: Optional[int] = None


class SeriesConfig(BaseModel):
    name: str
    total_games: int = Field(ge=1, le=100)
    game_config: GameConfig = Field(default_factory=GameConfig)
    players: list[PlayerConfig] = Field(min_length=5, max_length=7)


# ============ Event Models ============

class GameEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    ts: datetime = Field(default_factory=datetime.utcnow)
    series_id: str
    game_id: str
    type: EventType
    visibility: Visibility
    actor_id: Optional[str] = None
    target_id: Optional[str] = None
    payload: dict[str, Any] = {}


# ============ Actor Output Models ============

class ActorSpeech(BaseModel):
    content: str
    addressing: list[str] = []


class ActorVote(BaseModel):
    vote: str  # player_id or "no_lynch"
    reasoning: str


class ActorNightChoice(BaseModel):
    target: str
    reasoning: str


# ============ Reflection Models ============

class DeltaUpdate(BaseModel):
    action: str  # "add", "update", "remove"
    item: Optional[CheatsheetItem] = None
    item_id: Optional[str] = None
    reasoning: str
    source_event: str = ""  # The specific game event that led to this lesson


class ReflectorOutput(BaseModel):
    player_id: str
    game_analysis: str
    delta_updates: list[DeltaUpdate]
    overall_assessment: str


class CuratorDecision(BaseModel):
    delta_index: int
    decision: str  # "accept", "reject", "merge"
    reasoning: str
    merge_with_id: Optional[str] = None
    source_event: str = ""  # Preserved from reflector - the game event that taught this lesson


class CuratorOutput(BaseModel):
    player_id: str
    decisions: list[CuratorDecision]
    score_adjustments: list[dict[str, Any]] = []
    prune_items: list[dict[str, Any]] = []
    final_cheatsheet: Cheatsheet


# ============ API Response Models ============

class SeriesResponse(BaseModel):
    id: str
    name: str
    status: SeriesStatus
    total_games: int
    current_game_number: int
    config: SeriesConfig
    created_at: datetime


class GameResponse(BaseModel):
    id: str
    series_id: str
    game_number: int
    status: GamePhase
    winner: Optional[Winner] = None
    players: list[PlayerState]
    day_number: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PlayerCheatsheetResponse(BaseModel):
    player_id: str
    player_name: str
    cheatsheet: Cheatsheet
    games_played: int
