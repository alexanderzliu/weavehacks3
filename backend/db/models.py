"""SQLAlchemy ORM models for Mafia ACE."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Series(Base):
    __tablename__ = "series"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(
        String, nullable=False, default="pending"
    )  # pending, in_progress, stop_requested, completed
    total_games = Column(Integer, nullable=False)
    current_game_number = Column(Integer, default=0)
    config = Column(JSON, nullable=False)  # SeriesConfig as JSON
    random_seed = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    players = relationship("Player", back_populates="series", cascade="all, delete-orphan")
    games = relationship("Game", back_populates="series", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"

    id = Column(String, primary_key=True)
    series_id = Column(String, ForeignKey("series.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    model_provider = Column(String, nullable=False)  # anthropic, openai, google
    model_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    series = relationship("Series", back_populates="players")
    cheatsheets = relationship("Cheatsheet", back_populates="player", cascade="all, delete-orphan")
    game_players = relationship("GamePlayer", back_populates="player", cascade="all, delete-orphan")


class Game(Base):
    __tablename__ = "games"

    id = Column(String, primary_key=True)
    series_id = Column(String, ForeignKey("series.id", ondelete="CASCADE"), nullable=False)
    game_number = Column(Integer, nullable=False)
    status = Column(
        String, nullable=False, default="pending"
    )  # pending, day, voting, night, completed
    winner = Column(String, nullable=True)  # mafia, town, or null
    day_number = Column(Integer, default=0)
    random_seed = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    series = relationship("Series", back_populates="games")
    game_players = relationship("GamePlayer", back_populates="game", cascade="all, delete-orphan")
    events = relationship("GameEvent", back_populates="game", cascade="all, delete-orphan")


class GamePlayer(Base):
    """Junction table for game-player relationship with role assignment."""

    __tablename__ = "game_players"

    id = Column(String, primary_key=True)
    game_id = Column(String, ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    player_id = Column(String, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # mafia, doctor, deputy, townsperson
    is_alive = Column(Boolean, default=True)
    eliminated_day = Column(Integer, nullable=True)
    elimination_type = Column(String, nullable=True)  # lynched, killed

    # Relationships
    game = relationship("Game", back_populates="game_players")
    player = relationship("Player", back_populates="game_players")


class Cheatsheet(Base):
    __tablename__ = "cheatsheets"

    id = Column(String, primary_key=True)
    player_id = Column(String, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False, default=0)
    items = Column(JSON, nullable=False, default=list)  # List of CheatsheetItem dicts
    created_at = Column(DateTime, default=datetime.utcnow)
    created_after_game = Column(
        Integer, nullable=True
    )  # Game number this version was created after

    # Relationships
    player = relationship("Player", back_populates="cheatsheets")

    __table_args__ = (Index("idx_cheatsheet_player_version", "player_id", "version"),)


class GameEvent(Base):
    __tablename__ = "game_events"

    id = Column(String, primary_key=True)
    series_id = Column(String, ForeignKey("series.id", ondelete="CASCADE"), nullable=False)
    game_id = Column(String, ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    ts = Column(DateTime, default=datetime.utcnow)
    type = Column(String, nullable=False)  # EventType enum value
    visibility = Column(String, nullable=False)  # public, mafia, private, viewer
    actor_player_id = Column(String, ForeignKey("players.id"), nullable=True)
    target_player_id = Column(String, ForeignKey("players.id"), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)

    # Relationships
    game = relationship("Game", back_populates="events")

    __table_args__ = (
        Index("idx_game_events_game_ts", "game_id", "ts"),
        Index("idx_game_events_game_type", "game_id", "type"),
    )
