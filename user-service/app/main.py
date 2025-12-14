import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional

import redis
from app.models import (HealthCheckResponse, UserCreateRequest, UserResponse,
                        UserStatus, UserUpdateRequest)
from db.db import (close_db_connection, create_user_in_db, delete_user_from_db,
                   get_users_from_db, init_db, update_user_in_db)
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import EmailStr
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.middleware.base import BaseHTTPMiddleware

# Import environment variables
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
TTL_SECONDS = int(os.getenv("TTL_SECONDS"))

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

# Redis connection
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)


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
async def create_user(user: UserCreateRequest, request: Request):
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

    if not user.first_name or user.first_name.strip() == "":
        logger.warning(f"CREATE USER [{request_id}]: Missing first name")
        raise HTTPException(status_code=400, detail="Missing first name")

    if not user.last_name or user.last_name.strip() == "":
        logger.warning(f"CREATE USER [{request_id}]: Missing last name")
        raise HTTPException(status_code=400, detail="Missing last name")

    if not user.status or user.status not in ['Official', 'Non-Official']:
        logger.warning(
            f"CREATE USER [{request_id}]: Invalid or missing status")
        raise HTTPException(
            status_code=400, detail="Missing or invalid user status")

    if not user.username or user.username.strip() == "":
        logger.warning(f"CREATE USER [{request_id}]: Missing username")
        raise HTTPException(status_code=400, detail="Missing username")

    if not user.email or user.email.strip() == "":
        logger.warning(f"CREATE USER [{request_id}]: Missing email")
        raise HTTPException(status_code=400, detail="Missing email")

    logger.info(f"CREATE USER [{request_id}]: Adding user to DB")
    new_user = create_user_in_db(user)

    # Redis caching
    logger.info(f"CREATE USER [{request_id}]: Caching user data in Redis")
    try:
        cached = redis_client.setex(f"user:{new_user.id}",
                                    TTL_SECONDS, new_user.model_dump_json())
        if not cached:
            logger.warning(
                f"CREATE USER [{request_id}]: Failed to cache user data in Redis for user ID {new_user.id}")
        else:
            logger.info(
                f"CREATE USER [{request_id}]: User data cached in Redis for user ID {new_user.id}")
    except redis.RedisError as e:
        logger.error(
            f"CREATE USER [{request_id}]: Error caching user data in Redis for user ID {new_user.id}: {e}")

    logger.info(
        f"CREATE USER [{request_id}]: User created with ID {new_user.id}")

    return new_user


@app.get("/users", response_model=List[UserResponse])
async def get_user(request: Request,
                   user_id: Optional[str] = Query(default=None),
                   status: Optional[UserStatus] = Query(default=None),
                   username: Optional[str] = Query(
                       default=None, min_length=1, max_length=100),
                   email: Optional[EmailStr] = Query(
                       default=None, min_length=5, max_length=255)
                   ):
    """
    Retrieve users matching optional filter criteria.

    This endpoint returns a list of users filtered by any combination of
    `user_id`, `status`, `username`, or `email`. All query parameters are optional.
    If no parameters are provided, all users may be returned.

    A 404 Not Found error is raised if no users match the given filters.

    Args:
        request (Request): The incoming FastAPI request object.
        user_id (str, optional): Filter by a specific user ID.
        status (UserStatus, optional): Filter by the user's status.
        username (str, optional): Filter by username.
        email (EmailStr, optional): Filter by email address.

    Raises:
        HTTPException (404): If no users match the provided filters.
        HTTPException (500): If an unexpected error occurs during retrieval.

    Returns:
        List[UserResponse]: A list of users that match the filter criteria.
    """
    request_id = request.state.request_id

    logger.info(f"GET USER [{request_id}]: request received")

    # Check Redis cache if filtering by user_id only
    if user_id and not (status or username or email):
        logger.info(
            f"GET USER [{request_id}]: Checking Redis cache for user ID {user_id}")
        try:
            cached_user = redis_client.get(f"user:{user_id}")
            if cached_user:
                logger.info(
                    f"GET USER [{request_id}]: CACHE HIT - Retrieved user ID {user_id} from Redis cache")
                return [UserResponse.model_validate(json.loads(cached_user))]
            else:
                logger.info(
                    f"GET USER [{request_id}]: CACHE MISS - User ID {user_id} not found in Redis cache")
        except redis.RedisError as e:
            logger.error(
                f"GET USER [{request_id}]: Error accessing Redis cache for user ID {user_id}: {e}")

    properties = {}

    if user_id:
        properties['id'] = user_id
    if status:
        properties['status'] = status
    if username:
        properties['username'] = username
    if email:
        properties['email'] = email

    logger.info(
        f"GET USER [{request_id}]: Retrieving user(s) with properties {properties}")
    users = get_users_from_db(properties)

    if not users:
        logger.warning(
            f"GET USER [{request_id}]: No user(s) found with properties {properties}")
        raise HTTPException(
            status_code=404, detail=f"No user(s) found with properties: {properties}")

    logger.info(
        f"GET USER [{request_id}]: User(s) with properties {properties} successfully retrieved")

    # Potential to enable Redis caching for multiple users
    """ # Update Redis cache
    if len(users) <= 100:
        logger.info(
            f"GET USER [{request_id}]: Updating Redis cache for retrieved users")
        for user in users:
            try:
                cached = redis_client.setex(f"user:{user.id}",
                                            TTL_SECONDS, user.model_dump_json())
                if not cached:
                    logger.warning(
                        f"GET USER [{request_id}]: Failed to update Redis cache for user ID {user.id}")
                else:
                    logger.info(
                        f"GET USER [{request_id}]: Redis cache updated for user ID {user.id}")
            except redis.RedisError as e:
                logger.error(
                    f"GET USER [{request_id}]: Error updating Redis cache for user ID {user.id}: {e}") """

    return users


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_update: UserUpdateRequest, request: Request):
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

    # Update Redis cache
    logger.info(
        f"UPDATE USER [{request_id}]: Updating Redis cache for user ID {user_id}")
    try:
        cached = redis_client.setex(f"user:{updated_user.id}",
                                    TTL_SECONDS, updated_user.model_dump_json())
        if not cached:
            logger.warning(
                f"UPDATE USER [{request_id}]: Failed to update Redis cache for user ID {user_id}")
        else:
            logger.info(
                f"UPDATE USER [{request_id}]: Redis cache updated for user ID {user_id}")
    except redis.RedisError as e:
        logger.error(
            f"UPDATE USER [{request_id}]: Error updating Redis cache for user ID {user_id}: {e}")

    logger.info(
        f"UPDATE USER [{request_id}]: User with ID {user_id} successfully updated")
    return updated_user


@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: str, request: Request):
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

    # Remove from Redis cache
    logger.info(
        f"DELETE USER [{request_id}]: Removing user ID {user_id} from Redis cache")
    try:
        redis_client.delete(f"user:{user_id}")
    except redis.RedisError as e:
        logger.error(
            f"DELETE USER [{request_id}]: Error removing user ID {user_id} from Redis cache: {e}")

    logger.info(
        f"DELETE USER [{request_id}]: User with ID {user_id} successfully deleted")
