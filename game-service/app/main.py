import logging
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

from app.models import (CardInfo, CompletedGameInfo, GameCreateRequest,
                        GameResponse, GameUpdateRequest, HealthCheckResponse)
from db.db import (close_db_connection, create_game_in_db, delete_game_from_db,
                   get_games_from_db, init_db, update_game_in_db)
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("app/logs/game_service.txt"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    close_db_connection()

app = FastAPI(lifespan=lifespan)

# Middleware for request ID


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        return response


app.add_middleware(RequestIDMiddleware)

# Global exception handlers


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, e: IntegrityError):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(f"Integrity Error [{request_id}]: {e}")
    return JSONResponse(
        status_code=409,
        content={"detail": "Postgres Integrity Error"}
    )


@app.exception_handler(OperationalError)
async def operational_error_handler(request: Request, e: OperationalError):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"Operational Error [{request_id}]: {e}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Database connection error"}
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, e: RequestValidationError):
    request_id = getattr(request.state, "request_id", "unknown")

    errors = e.errors()
    if errors:
        for i in range(0, len(errors)):
            logger.warning(
                f"Validation Error [{request_id}]: {errors[i].get('msg', 'Unknown validation error')}")
    else:
        logger.warning(
            f"Validation Error [{request_id}]: No details available")

    return JSONResponse(
        status_code=400,
        content={
            "detail": [
                {
                    "loc": err["loc"] if "loc" in err else "",
                    "msg": err["msg"] if "msg" in err else "",
                    "type": err["type"] if "type" in err else ""
                } for err in e.errors()
            ]
        }
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint for the game service.

    returns status 200 with the following JSON structure:

        dict: {
            "service": "game-service",
            "status": "healthy",
            "dependencies": { ... }
        }

    Or status 503 if the service or its dependencies are unhealthy.
    """

    return HealthCheckResponse(
        service="game-service",
        status="healthy",
        dependencies=None
    )


@app.post("/games", status_code=201, response_model=GameResponse)
async def create_game(game: GameCreateRequest, request: Request):
    """
    Create a new game.

    This endpoint accepts game details and creates a new game record in the
    database. Required fields are validated to ensure they are present and
    non-empty. If validation fails, a 400 Bad Request error is returned.

    A unique request ID is used for logging to aid in tracing and debugging.

    Args:
        game (GameCreateRequest): The request body containing the game details,
            including league, venue, home team, away team, level, and scheduled
            time.
        request (Request): The incoming HTTP request, used to extract the
            request ID for logging.

    Returns:
        GameResponse: The newly created game, including its generated ID and
        timestamps.

    Raises:
        HTTPException: 
            - 400 Bad Request if any required field is missing or empty.
    """

    request_id = request.state.request_id

    logger.info(f"CREATE GAME [{request_id}]: request received")

    if not game.league or game.league.strip() == "":
        logger.warning(f"CREATE GAME [{request_id}]: Missing league")
        raise HTTPException(status_code=400, detail="Missing league")
    if not game.venue or game.venue.strip() == "":
        logger.warning(f"CREATE GAME [{request_id}]: Missing venue")
        raise HTTPException(status_code=400, detail="Missing venue")
    if not game.home_team or game.home_team.strip() == "":
        logger.warning(f"CREATE GAME [{request_id}]: Missing home_team")
        raise HTTPException(status_code=400, detail="Missing home_team")
    if not game.away_team or game.away_team.strip() == "":
        logger.warning(f"CREATE GAME [{request_id}]: Missing away_team")
        raise HTTPException(status_code=400, detail="Missing away_team")
    if not game.level or game.level.strip() == "":
        logger.warning(f"CREATE GAME [{request_id}]: Missing level")
        raise HTTPException(status_code=400, detail="Missing level")
    if not game.scheduled_time:
        logger.warning(f"CREATE GAME [{request_id}]: Missing scheduled_time")
        raise HTTPException(status_code=400, detail="Missing scheduled_time")

    logger.info(f"CREATE GAME [{request_id}]: Adding game to DB")
    new_game = create_game_in_db(game)

    logger.info(
        f"CREATE GAME [{request_id}]: Game created with ID {new_game.id}")

    return new_game


@app.get("/games", response_model=List[GameResponse])
async def get_game(request: Request,
                   game_id: Optional[str] = Query(default=None),
                   league: Optional[str] = Query(
                       default=None, min_length=1, max_length=100),
                   venue: Optional[str] = Query(
                       default=None, min_length=1, max_length=255),
                   home_team: Optional[str] = Query(
                       default=None, min_length=1, max_length=100),
                   away_team: Optional[str] = Query(
                       default=None, min_length=1, max_length=100),
                   level: Optional[str] = Query(
                       default=None, min_length=1, max_length=100),
                   game_completed: Optional[bool] = Query(default=None)
                   ):
    """
    Retrieve games matching the provided query parameters.

    This endpoint returns a list of games that match the specified filter
    criteria. All query parameters are optional, and only the parameters
    provided are used to filter results. If no query parameters are supplied,
    all games are returned.

    A unique request ID is used for logging to aid in tracing and debugging.

    Args:
        request (Request): The incoming HTTP request, used to extract the
            request ID for logging.
        game_id (Optional[str]): Filter by the unique game ID.
        league (Optional[str]): Filter by league name.
        venue (Optional[str]): Filter by venue name.
        home_team (Optional[str]): Filter by home team name.
        away_team (Optional[str]): Filter by away team name.
        level (Optional[str]): Filter by competition level.
        game_completed (Optional[bool]): Filter by completion status of the game.

    Returns:
        List[GameResponse]: A list of games matching the provided filters.

    Raises:
        HTTPException:
            - 404 Not Found if no games match the provided filter criteria.
    """

    request_id = request.state.request_id

    properties = {}

    if game_id:
        properties["id"] = game_id
    if league:
        properties["league"] = league
    if venue:
        properties["venue"] = venue
    if home_team:
        properties["home_team"] = home_team
    if away_team:
        properties["away_team"] = away_team
    if level:
        properties["level"] = level
    if game_completed is not None:
        properties["game_completed"] = game_completed

    logger.info(
        f"GET GAMES [{request_id}]: Retrieving game(s) with properties {properties}")
    games = get_games_from_db(properties)

    if not games:
        logger.warning(
            f"GET GAMES [{request_id}]: No game(s) found with properties {properties}")
        raise HTTPException(
            status_code=404, detail=f"No game(s) found with properties: {properties}")

    logger.info(
        f"GET GAMES [{request_id}]: Game(s) with properties {properties} successfully retrieved")
    return games


@app.put("/games/{game_id}", response_model=GameResponse)
async def update_game(game_id: str, game_update: GameUpdateRequest, request: Request):
    """
    Update an existing game.

    This endpoint updates the fields of an existing game identified by its
    unique game ID. Only the fields provided in the request body are updated.
    If the specified game does not exist, a 404 Not Found error is returned.

    A unique request ID is used for logging to aid in tracing and debugging.

    Args:
        game_id (str): The unique identifier of the game to update.
        game_update (GameUpdateRequest): The request body containing the fields
            to update for the game.
        request (Request): The incoming HTTP request, used to extract the
            request ID for logging.

    Returns:
        GameResponse: The updated game record.

    Raises:
        HTTPException:
            - 404 Not Found if no game exists with the specified game ID.
    """

    request_id = request.state.request_id

    logger.info(f"UPDATE GAME [{request_id}]: Updating game with ID {game_id}")
    updated_game = update_game_in_db(game_id, game_update)

    if not updated_game:
        logger.warning(
            f"UPDATE GAME [{request_id}]: No game found with ID {game_id}")
        raise HTTPException(
            status_code=404, detail=f"No game found with ID: {game_id}")

    logger.info(
        f"UPDATE GAME [{request_id}]: Game with ID {game_id} successfully updated")
    return updated_game


@app.delete("/games/{game_id}", status_code=204)
async def delete_game(game_id: str, request: Request):
    """
    Delete an existing game.

    This endpoint permanently deletes the game identified by its unique game ID.
    If the specified game does not exist, a 404 Not Found error is returned.
    On successful deletion, no response body is returned.

    A unique request ID is used for logging to aid in tracing and debugging.

    Args:
        game_id (str): The unique identifier of the game to delete.
        request (Request): The incoming HTTP request, used to extract the
            request ID for logging.

    Returns:
        None

    Raises:
        HTTPException:
            - 404 Not Found if no game exists with the specified game ID.
    """

    request_id = request.state.request_id

    logger.info(f"DELETE GAME [{request_id}]: Deleting game with ID {game_id}")
    deleted = delete_game_from_db(game_id)

    if not deleted:
        logger.warning(
            f"DELETE GAME [{request_id}]: No game found with ID {game_id}")
        raise HTTPException(
            status_code=404, detail=f"No game found with ID: {game_id}")

    logger.info(
        f"DELETE GAME [{request_id}]: Game with ID {game_id} successfully deleted")
