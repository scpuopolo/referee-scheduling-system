import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from app.models import UserCreateRequest, UserUpdateRequest
from sqlmodel import Field, Session, SQLModel, create_engine, delete, select

# Load the Postgres DSN (connection string) from environment variables
PG_DSN = os.getenv("PG_DSN")

# Create the SQLAlchemy engine that connects to the database
engine = create_engine(PG_DSN)


class UserModel(SQLModel, table=True):
    # Define the UserModel
    __tablename__ = "users"

    id: str = Field(primary_key=True, default_factory=lambda: str(uuid4()))
    status: str = Field(nullable=False)
    first_name: str = Field(nullable=False)
    last_name: str = Field(nullable=False)
    username: str = Field(unique=True, nullable=False)
    email: str = Field(unique=True, nullable=False)
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


def create_user_in_db(user: UserCreateRequest) -> UserModel:
    """Create a completely new user in the database."""
    with get_session() as session:
        new_user = UserModel(
            id=str(uuid4()),
            status=user.status,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            email=user.email,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return new_user


def get_user_from_db(properties: dict) -> List[UserModel] | None:
    """Retrieve all users from the database by user properties."""
    with get_session() as session:
        statement = select(UserModel)
        filters = []

        if user_id := properties.get('id'):
            filters.append(UserModel.id == user_id)
        if status := properties.get('status'):
            filters.append(UserModel.status == status)
        if username := properties.get('username'):
            filters.append(UserModel.username == username)
        if email := properties.get('email'):
            filters.append(UserModel.email == email)

        if filters:
            statement = statement.where(*filters)

        return session.exec(statement).all()


def update_user_in_db(user_id: str, user_update: UserUpdateRequest) -> UserModel | None:
    """Update an existing user in the database."""
    with get_session() as session:
        statement = select(UserModel).where(UserModel.id == user_id)
        user = session.exec(statement).first()

        if not user:
            return None

        if user_update.status is not None:
            user.status = user_update.status
        if user_update.first_name is not None:
            user.first_name = user_update.first_name
        if user_update.last_name is not None:
            user.last_name = user_update.last_name
        if user_update.username is not None:
            user.username = user_update.username
        if user_update.email is not None:
            user.email = user_update.email

        user.updated_at = datetime.now(timezone.utc)

        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def delete_user_from_db(user_id):
    """Delete a user from the database by user ID."""
    with get_session() as session:
        statement = delete(UserModel).where(UserModel.id == user_id)
        result = session.exec(statement)
        session.commit()
        return result.rowcount > 0
