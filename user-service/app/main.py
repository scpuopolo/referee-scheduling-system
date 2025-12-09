import logging
import uuid
from contextlib import asynccontextmanager

from app.models import (HealthCheckResponse, UserCreateRequest, UserResponse,
                        UserUpdateRequest)
from db.db import (close_db_connection, create_user_in_db, delete_user_from_db,
                   get_user_from_db, init_db, update_user_in_db)
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.middleware.base import BaseHTTPMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app/logs/user_service.txt",
                            mode="a"),  # write to file
        logging.StreamHandler()  # also show in console
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
        content={"detail": "Duplicate username or email"}
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
                    "loc": err["loc"],
                    "msg": err["msg"],
                    "type": err["type"]
                } for err in e.errors()
            ]
        }
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint for the user service.

    returns status 200 with the following JSON structure:

        dict: {
            "service": "user-service",
            "status": "healthy",
            "dependencies": { ... }
        }

    Or status 503 if the service or its dependencies are unhealthy.
    """

    return HealthCheckResponse(
        service="user-service",
        status="healthy",
        dependencies=None
    )


@app.post("/users", status_code=201, response_model=UserResponse)
def create_user(user: UserCreateRequest, request: Request):
    """
    Create a new user.

    This endpoint accepts a UserCreateRequest payload, validates required fields,
    and inserts a new user record into the database. On successful creation, it
    returns the newly created user along with a 201 Created status code.

    Raises:
        HTTPException (400): If one or more required fields are missing or invalid.
        HTTPException (500): If an unexpected error occurs during user creation.

    Returns:
        UserResponse: The newly created user's information.
    """
    request_id = request.state.request_id

    logger.info(f"CREATE USER [{request_id}]: request received")

    if not user.first_name:
        logger.warning(f"CREATE USER [{request_id}]: Missing first name")
        raise HTTPException(status_code=400, detail="Missing first name")

    if not user.last_name:
        logger.warning(f"CREATE USER [{request_id}]: Missing last name")
        raise HTTPException(status_code=400, detail="Missing last name")

    if not user.status or user.status not in ['Official', 'Non-Official']:
        logger.warning(
            f"CREATE USER [{request_id}]: Invalid or missing status")
        raise HTTPException(
            status_code=400, detail="Missing or invalid user status")

    if not user.username:
        logger.warning(f"CREATE USER [{request_id}]: Missing username")
        raise HTTPException(status_code=400, detail="Missing username")

    if not user.email:
        logger.warning(f"CREATE USER [{request_id}]: Missing email")
        raise HTTPException(status_code=400, detail="Missing email")

    logger.info(f"CREATE USER [{request_id}]: Adding user to DB")
    new_user = create_user_in_db(user)

    logger.info(
        f"CREATE USER [{request_id}]: User created with ID {new_user.id}")

    return new_user


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, request: Request):
    """
    Retrieve a user's details by their user ID.

    This endpoint looks up and returns a user's information based on the
    provided `user_id`. If the user exists, their details are returned with
    a 200 OK status. If no matching user is found, a 404 Not Found error
    is raised.

    Args:
        user_id (str): The unique identifier of the user to retrieve.

    Raises:
        HTTPException (404): If no user exists with the given `user_id`.
        HTTPException (500): If an unexpected error occurs during retrieval.

    Returns:
        UserResponse: The user's information if found.
    """
    request_id = request.state.request_id

    logger.info(f"GET USER [{request_id}]: Retrieving user with ID {user_id}")
    user = get_user_from_db(user_id)

    if not user:
        logger.warning(
            f"GET USER [{request_id}]: No user found with ID {user_id}")
        raise HTTPException(
            status_code=404, detail=f"No user found with ID: {user_id}")

    logger.info(
        f"GET USER [{request_id}]: User with ID {user_id} successfully retrieved")
    return user


@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: str, user_update: UserUpdateRequest, request: Request):
    """
    Update an existing user's details.

    This endpoint applies the fields provided in the `UserUpdateRequest` payload
    to the user identified by `user_id`. Only the supplied fields are updated.
    If the user exists, the updated user data is returned with a 200 OK status.
    If no matching user is found, a 404 Not Found error is raised.

    Args:
        user_id (str): The unique identifier of the user to update.
        user_update (UserUpdateRequest): The set of fields to modify for the user.

    Raises:
        HTTPException (404): If no user exists with the given `user_id`.
        HTTPException (400): If provided update data is invalid.
        HTTPException (500): If an unexpected error occurs during the update.

    Returns:
        UserResponse: The user's updated information.
    """
    request_id = request.state.request_id

    logger.info(f"UPDATE USER [{request_id}]: Updating user with ID {user_id}")
    updated_user = update_user_in_db(user_id, user_update)

    if not updated_user:
        logger.warning(
            f"UPDATE USER [{request_id}]: No user found with ID {user_id}")
        raise HTTPException(
            status_code=404, detail=f"No user found with ID: {user_id}")

    logger.info(
        f"UPDATE USER [{request_id}]: User with ID {user_id} successfully updated")
    return updated_user


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: str, request: Request):
    """
    Delete a user by their user ID.

    This endpoint removes the user identified by `user_id` from the database.
    On successful deletion, it returns a 204 No Content status. If no user
    exists with the given ID, a 404 Not Found error is raised.

    Args:
        user_id (str): The unique identifier of the user to delete.

    Raises:
        HTTPException (404): If no user exists with the given `user_id`.
        HTTPException (500): If an unexpected error occurs during deletion.

    Returns:
        None: The response has no content on successful deletion.
    """
    request_id = request.state.request_id

    logger.info(f"DELETE USER [{request_id}]: Deleting user with ID {user_id}")
    deleted = delete_user_from_db(user_id)

    if not deleted:
        logger.warning(
            f"DELETE USER [{request_id}]: No user found with ID {user_id}")
        raise HTTPException(
            status_code=404, detail=f"No user found with ID: {user_id}")

    logger.info(
        f"DELETE USER [{request_id}]: User with ID {user_id} successfully deleted")
