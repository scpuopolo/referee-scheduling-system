import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from app.models import AssignmentCreateRequest, AssignmentUpdateRequest
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Session, SQLModel, create_engine, delete, select

# Load the Postgres DSN (connection string) from environment variables
PG_DSN = os.getenv("PG_ASSIGNMENT_DSN")

# Create the SQLAlchemy engine that connects to the database
engine = create_engine(PG_DSN)


class AssignmentModel(SQLModel, table=True):
    # Define the Assignment Model
    __tablename__ = "assignments"

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()))
    game_id: str = Field(unique=True, nullable=False)
    referees: Optional[List[dict]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True))
    assigned_at: datetime
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


def create_assignment_in_db(assignment: AssignmentCreateRequest) -> AssignmentModel:
    """Create a new assignment in the database."""
    with get_session() as session:
        new_assignment = AssignmentModel(
            id=str(uuid4()),
            game_id=assignment.game_id,
            referees=[referee.model_dump(
            ) for referee in assignment.referees] if assignment.referees else None,
            assigned_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(new_assignment)
        session.commit()
        session.refresh(new_assignment)
        return new_assignment


def get_assignments_from_db(properties: dict) -> List[AssignmentModel] | None:
    """Retrieve assignments from the database based on provided properties."""
    with get_session() as session:
        statement = select(AssignmentModel)

        filters = []

        if "assignment_id" in properties:
            filters.append(AssignmentModel.id == properties["assignment_id"])
        if "game_id" in properties:
            filters.append(AssignmentModel.game_id == properties["game_id"])
        if "referee_id" in properties:
            filters.append(
                AssignmentModel.referees.contains(
                    [{"referee_id": properties["referee_id"]}]
                )
            )

        if filters:
            statement = statement.where(*filters)

        return session.exec(statement).all()


def update_assignment_in_db(assignment_id: str, assignment_update: AssignmentUpdateRequest) -> AssignmentModel | None:
    """Update an existing assignment in the database."""
    with get_session() as session:
        statement = select(AssignmentModel).where(
            AssignmentModel.id == assignment_id)
        assignment = session.exec(statement).first()

        if not assignment:
            return None

        if assignment_update.referees is not None:
            assignment.referees = [referee.model_dump()
                                   for referee in assignment_update.referees]

        assignment.updated_at = datetime.now(timezone.utc)

        session.add(assignment)
        session.commit()
        session.refresh(assignment)
        return assignment


def delete_assignment_from_db(assignment_id: str):
    """Delete an assignment from the database by assignment ID."""
    with get_session() as session:
        statement = delete(AssignmentModel).where(
            AssignmentModel.id == assignment_id)
        result = session.exec(statement)
        session.commit()
        return result.rowcount > 0
