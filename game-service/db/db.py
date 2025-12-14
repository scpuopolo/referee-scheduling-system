import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from app.models import GameCreateRequest, GameUpdateRequest
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Session, SQLModel, create_engine, delete, select

# Load the Postgres DSN (connection string) from environment variables
PG_DSN = os.getenv("PG_GAME_DSN")

# Create the SQLAlchemy engine that connects to the database
engine = create_engine(PG_DSN)


class GameModel(SQLModel, table=True):
    # Define the GameModel
    __tablename__ = "games"

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()))
    league: str = Field(nullable=False)
    venue: str = Field(nullable=False)
    home_team: str = Field(nullable=False)
    away_team: str = Field(nullable=False)
    level: str = Field(nullable=False)
    halves_length_minutes: int = Field(nullable=False, default=45)
    game_completed: bool = Field(nullable=False, default=False)
    result: Optional[dict] = Field(
        default=None, sa_column=Column(JSONB, nullable=True))
    scheduled_time: datetime = Field(nullable=False)
    created_at: datetime
    updated_at: datetime


def init_db():
    """Create the database tables."""
    SQLModel.metadata.create_all(engine)


def close_db_connection():
    """Close the database connection cleanly."""
    engine.dispose()


@contextmanager
def get_session():
    """Context manager for a short-lived session."""
    with Session(engine) as session:
        yield session


def create_game_in_db(game: GameCreateRequest) -> GameModel:
    """Create a completely new game in the database."""
    with get_session() as session:
        new_game = GameModel(
            id=str(uuid4()),
            league=game.league,
            venue=game.venue,
            home_team=game.home_team,
            away_team=game.away_team,
            level=game.level,
            halves_length_minutes=game.halves_length_minutes,
            game_completed=False,
            result=None,
            scheduled_time=game.scheduled_time,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(new_game)
        session.commit()
        session.refresh(new_game)
        return new_game


def get_games_from_db(properties: dict) -> List[GameModel] | None:
    """Retrieve all games from the database by game properties."""
    with get_session() as session:
        statement = select(GameModel)
        filters = []

        if game_id := properties.get('id'):
            filters.append(GameModel.id == game_id)
        if league := properties.get('league'):
            filters.append(GameModel.league == league)
        if venue := properties.get('venue'):
            filters.append(GameModel.venue == venue)
        if home_team := properties.get('home_team'):
            filters.append(GameModel.home_team == home_team)
        if away_team := properties.get('away_team'):
            filters.append(GameModel.away_team == away_team)
        if level := properties.get('level'):
            filters.append(GameModel.level == level)
        if game_completed := properties.get('game_completed'):
            filters.append(GameModel.game_completed == game_completed)

        if filters:
            statement = statement.where(*filters)

        return session.exec(statement).all()


def update_game_in_db(game_id: str, game_update: GameUpdateRequest) -> GameModel | None:
    """Update an existing game in the database."""
    with get_session() as session:
        statement = select(GameModel).where(GameModel.id == game_id)
        game = session.exec(statement).first()

        if not game:
            return None

        if game_update.league is not None:
            game.league = game_update.league
        if game_update.venue is not None:
            game.venue = game_update.venue
        if game_update.home_team is not None:
            game.home_team = game_update.home_team
        if game_update.away_team is not None:
            game.away_team = game_update.away_team
        if game_update.level is not None:
            game.level = game_update.level
        if game_update.halves_length_minutes is not None:
            game.halves_length_minutes = game_update.halves_length_minutes
        if game_update.scheduled_time is not None:
            game.scheduled_time = game_update.scheduled_time
        if game_update.game_completed is not None:
            game.game_completed = game_update.game_completed
        if game_update.result is not None:
            existing_result = game.result or {}
            update_result = game_update.result.model_dump(exclude_unset=True)

            # Merge existing with updates, but overwrite cards_issued if provided
            merged_result = {**existing_result, **update_result}

            if "cards_issued" in update_result:
                merged_result["cards_issued"] = update_result["cards_issued"]

            game.result = merged_result
        else:
            # If the client explicitly sends null, wipe the result
            game.result = None

        game.updated_at = datetime.now(timezone.utc)

        session.add(game)
        session.commit()
        session.refresh(game)
        return game


def delete_game_from_db(game_id):
    """Delete a game from the database by game ID."""
    with get_session() as session:
        statement = delete(GameModel).where(GameModel.id == game_id)
        result = session.exec(statement)
        session.commit()
        return result.rowcount > 0
