import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from app.models import (AssignmentCreateRequest, AssignmentResponse,
                        AssignmentUpdateRequest, HealthCheckResponse)
from db.db import (close_db_connection, create_assignment_in_db,
                   delete_assignment_from_db, get_assignments_from_db, init_db,
                   update_assignment_in_db)
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.middleware.base import BaseHTTPMiddleware

# External service bases
USER_SERVICE_BASE = os.getenv("USER_SERVICE_BASE", "http://user-service:8000")
GAME_SERVICE_BASE = os.getenv("GAME_SERVICE_BASE", "http://game-service:8000")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("app/logs/assignment_service.txt"),
        logging.StreamHandler()
    ]
)

logging.getLogger("httpx").setLevel(
    logging.WARNING)  # Reduce httpx logging noise
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    close_db_connection()

app = FastAPI(lifespan=lifespan)

# Middleware fpr request ID


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
        content={"detail": "Duplicate game_id"}
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


async def check_dependency_health(base_url: str) -> dict:
    """
    Check the health of a dependent service.

    args:

        base_url (str): Base URL of the dependent service.

    returns:

        dict: {
            "status": "healthy" or "unhealthy",
            "response_time_ms": float
            }
    """
    try:
        async with httpx.AsyncClient() as client:
            start_time = datetime.now(timezone.utc)
            response = await client.get(f"{base_url}/health")
            status = "healthy" if response.status_code == 200 else "unhealthy"
    except httpx.RequestError:
        status = "unhealthy"

    elapsed_ms = (datetime.now(timezone.utc) -
                  start_time).total_seconds() * 1000
    return {"status": status, "response_time_ms": elapsed_ms}


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint for the assignment service.

    returns:

        - HTTP 200 and JSON payload if the service and all dependencies are healthy:
            dict: {
                "service": "assignment-service",
                "status": "healthy",
                "dependencies": {
                    "user-service": {"status": "healthy", "response_time_ms": <float>},
                    "game-service": {"status": "healthy", "response_time_ms": <float>}
                }
            }

        - HTTP 503 and JSON payload if any dependency or the service is unhealthy:
            {
                "service": "assignment-service",
                "status": "unhealthy",
                "dependencies": { ... }
            }
    """
    dependencies = {
        "user-service": await check_dependency_health(USER_SERVICE_BASE),
        "game-service": await check_dependency_health(GAME_SERVICE_BASE),
    }

    # If any dependency is unhealthy, propagate a 503 response
    if any(dep["status"] != "healthy" for dep in dependencies.values()):
        return JSONResponse(
            status_code=503,
            content=HealthCheckResponse(
                service="assignment-service",
                status="unhealthy",
                dependencies=dependencies,
            ).model_dump()
        )

    # Otherwise, return a healthy response
    return HealthCheckResponse(
        service="assignment-service",
        status="healthy",
        dependencies=dependencies,
    )


@app.post("/assignments", status_code=201, response_model=AssignmentResponse)
async def create_assignment(assignment: AssignmentCreateRequest, request: Request):
    request_id = request.state.request_id

    logger.info(f"CREATE ASSIGNMENT [{request_id}]: Request received")

    if not assignment.game_id:
        logger.warning(f"CREATE ASSIGNMENT [{request_id}]: Missing game_id")
        raise HTTPException(status_code=400, detail="Missing game_id")

    # Validate game_id exists in game service DB
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GAME_SERVICE_BASE}/games?game_id={assignment.game_id}")

            if response.status_code != 200:
                logger.warning(
                    f"CREATE ASSIGNMENT [{request_id}]: game_id {assignment.game_id} not found in game service")
                raise HTTPException(
                    status_code=response.status_code, detail=response.json().get("detail", "Error from game service"))
    except httpx.RequestError as e:
        logger.error(
            f"CREATE ASSIGNMENT [{request_id}]: Error communicating with the game service: {e}")
        raise HTTPException(
            status_code=500, detail="Error communicating with the game service")

    if assignment.referees:
        # Validate an Official with given ID exists in user service DB
        try:
            async with httpx.AsyncClient() as client:
                for referee in assignment.referees:
                    response = await client.get(f"{USER_SERVICE_BASE}/users?user_id={referee.referee_id}&status=Official")

                    if response.status_code != 200:
                        logger.warning(
                            f"CREATE ASSIGNMENT [{request_id}]: Official with ID {referee.referee_id} not found in user service")
                        raise HTTPException(
                            status_code=response.status_code, detail=response.json().get("detail", "Error from user service"))
        except httpx.RequestError as e:
            logger.error(
                f"CREATE ASSIGNMENT [{request_id}]: Error communicating with the user service: {e}")
            raise HTTPException(
                status_code=500, detail="Error communicating with the user service")

    logger.info(f"CREATE ASSIGNMENT [{request_id}]: Adding assignment to DB")
    new_assignment = create_assignment_in_db(assignment)

    logger.info(
        f"CREATE ASSIGNMENT [{request_id}]: Assignment created with ID {new_assignment.id}")

    return new_assignment


@app.get("/assignments", response_model=List[AssignmentResponse])
async def get_assignments(request: Request,
                          assignment_id: Optional[str] = Query(default=None),
                          game_id: Optional[str] = Query(default=None),
                          referee_id: Optional[str] = Query(default=None)
                          ):
    request_id = request.state.request_id

    properties = {}

    if assignment_id:
        properties["assignment_id"] = assignment_id
    if game_id:
        properties["game_id"] = game_id
    if referee_id:
        properties["referee_id"] = referee_id

    logger.info(
        f"GET ASSIGNMENTS [{request_id}]: Retrieving assignment(s) with properties {properties}")
    assignments = get_assignments_from_db(properties)

    if not assignments:
        logger.warning(
            f"GET ASSIGNMENTS [{request_id}]: No assignment(s) found with properties {properties}")
        raise HTTPException(
            status_code=404, detail=f"No assignment(s) found with properties {properties}")

    logger.info(
        f"GET ASSIGNMENTS [{request_id}]: Assignment(s) with properties {properties} successfully retrieved")
    return assignments


@app.put("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(assignment_id: str, assignment_update: AssignmentUpdateRequest, request: Request):
    request_id = request.state.request_id

    logger.info(f"UPDATE ASSIGNMENT [{request_id}]: Request received")

    if assignment_update.referees:
        # Validate Official with given ID exists in user service DB
        try:
            async with httpx.AsyncClient() as client:
                for referee in assignment_update.referees:
                    response = await client.get(f"{USER_SERVICE_BASE}/users?user_id={referee.referee_id}&status=Official")

                    if response.status_code != 200:
                        logger.warning(
                            f"UPDATE ASSIGNMENT [{request_id}]: Official with ID {referee.referee_id} not found in user service")
                        raise HTTPException(
                            status_code=response.status_code, detail=response.json().get("detail", "Error from user service"))
        except httpx.RequestError as e:
            logger.error(
                f"UPDATE ASSIGNMENT [{request_id}]: Error communicating with the user service: {e}")
            raise HTTPException(
                status_code=500, detail="Error communicating with the user service")

    logger.info(
        f"UPDATE ASSIGNMENT [{request_id}]: Updating assignment with ID {assignment_id}")
    updated_assignment = update_assignment_in_db(
        assignment_id, assignment_update)

    if not updated_assignment:
        logger.warning(
            f"UPDATE ASSIGNMENT [{request_id}]: No assignment found with ID {assignment_id}")
        raise HTTPException(
            status_code=404, detail=f"No assignment found with ID {assignment_id}")

    logger.info(
        f"UPDATE ASSIGNMENT [{request_id}]: Assignment with ID {assignment_id} successfully updated")
    return updated_assignment


@app.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: str, request: Request):
    request_id = request.state.request_id

    logger.info(
        f"DELETE ASSIGNMENT [{request_id}]: Deleting assignment with ID {assignment_id}")
    deleted = delete_assignment_from_db(assignment_id)

    if not deleted:
        logger.warning(
            f"DELETE ASSIGNMENT [{request_id}]: No assignment found with ID {assignment_id}")
        raise HTTPException(
            status_code=404, detail=f"No assignment found with ID {assignment_id}")
    logger.info(
        f"DELETE ASSIGNMENT [{request_id}]: Assignment with ID {assignment_id} successfully deleted")

# Extra Routes


@app.get("/assignments/full-details/{assignment_id}")
async def get_assignments_full_details(assignment_id: str, request: Request):
    request_id = request.state.request_id

    logger.info(
        f"GET ASSIGNMENT FULL DETAILS [{request_id}]: Retrieving full details for assignment ID {assignment_id}")

    filter = {"assignment_id": assignment_id}

    logger.info(
        f"GET ASSIGNMENT FULL DETAILS [{request_id}]: Fetching assignment from DB")
    assignment = get_assignments_from_db(filter)

    if not assignment:
        logger.warning(
            f"GET ASSIGNMENT FULL DETAILS [{request_id}]: No assignment found with ID {assignment_id}")
        raise HTTPException(
            status_code=404, detail=f"No assignment found with ID {assignment_id}")
    else:
        assignment = AssignmentResponse.model_validate(assignment[0])

    logger.info(
        f"GET ASSIGNMENT FULL DETAILS [{request_id}]: Successfully retrieved assignment details")

    # Fetch game details from game service
    logger.info(
        f"GET ASSIGNMENT FULL DETAILS [{request_id}]: Fetching game details for game_id {assignment.game_id} from game service")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{GAME_SERVICE_BASE}/games?game_id={assignment.game_id}")
            if response.status_code != 200:
                logger.warning(
                    f"GET ASSIGNMENT FULL DETAILS [{request_id}]: game_id {assignment.game_id} not found in game service")
                raise HTTPException(status_code=response.status_code, detail=response.json().get(
                    "detail", "Error from game service"))

            game_details = response.json()[0]
    except httpx.RequestError as e:
        logger.error(
            f"GET ASSIGNMENT FULL DETAILS [{request_id}]: Error communicating with the game service: {e}")
        raise HTTPException(
            status_code=500, detail="Error communicating with the game service")

    if assignment.referees:
        # Fetch referee details from user service
        logger.info(
            f"GET ASSIGNMENT FULL DETAILS [{request_id}]: Fetching referee details from user service")

        referee_details = []
        try:
            async with httpx.AsyncClient() as client:
                for referee in assignment.referees:
                    response = await client.get(f"{USER_SERVICE_BASE}/users?user_id={referee.referee_id}")

                    if response.status_code != 200:
                        logger.warning(
                            f"GET ASSIGNMENT FULL DETAILS [{request_id}]: Official with ID {referee.referee_id} not found in user service")
                        raise HTTPException(
                            status_code=response.status_code, detail=response.json().get("detail", "Error from user service"))
                    ref_data = response.json()[0]
                    ref_data['position'] = referee.position
                    referee_details.append(ref_data)
        except httpx.RequestError as e:
            logger.error(
                f"GET ASSIGNMENT FULL DETAILS [{request_id}]: Error communicating with the user service: {e}")
            raise HTTPException(
                status_code=500, detail="Error communicating with the user service")

    full_details = {
        "assignment_id": assignment_id,
        "game": game_details,
        "referees": referee_details if assignment.referees else None
    }

    logger.info(
        f"GET ASSIGNMENT FULL DETAILS [{request_id}]: Successfully retrieved full assignment details")

    return full_details
