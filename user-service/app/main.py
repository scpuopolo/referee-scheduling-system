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
    Create a new user in the system.

    This endpoint accepts a `UserCreateRequest` payload, validates all required fields,
    inserts a new user record into the database, and caches the user in Redis. On success,
    it returns the newly created user's details along with a 201 Created status.

    Args:
        user (UserCreateRequest): The payload containing user details.
        request (Request): The FastAPI request object, used here to access the request ID for logging.

    Returns:
        UserResponse: The newly created user's information.

    Raises:
        HTTPException (400): If any required field is missing or invalid (first name, last name, username, email, status).
        HTTPException (500): If an unexpected error occurs during database insertion or caching.

    Notes:
        - User status must be either 'Official' or 'Non-Official'.
        - After successful creation, the user object is cached in Redis for faster future retrieval.
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
    Retrieve users based on optional filter criteria.

    This endpoint returns a list of users filtered by any combination of `user_id`, 
    `status`, `username`, or `email`. If no filters are provided, it may return all users. 
    When only `user_id` is provided, the endpoint will first attempt to retrieve the user 
    from the Redis cache before querying the database.

    Args:
        request (Request): The FastAPI request object, used for logging request ID.
        user_id (str, optional): Filter by a specific user ID.
        status (UserStatus, optional): Filter by the user's status ('Official' or 'Non-Official').
        username (str, optional): Filter by username (1-100 characters).
        email (EmailStr, optional): Filter by email address (5-255 characters).

    Returns:
        List[UserResponse]: A list of users that match the provided filter criteria.

    Raises:
        HTTPException (404): If no users match the provided filters.
        HTTPException (500): If an unexpected error occurs during retrieval or cache access.

    Notes:
        - If only `user_id` is provided, the Redis cache is checked first for faster retrieval.
        - Partial or combination filters are supported; any user matching all specified filters will be returned.
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

    return users


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_update: UserUpdateRequest, request: Request):
    """
    Update an existing user's details.

    This endpoint updates the user identified by `user_id` with the fields provided
    in the `UserUpdateRequest` payload. Only the supplied fields are modified, and
    other fields remain unchanged. After a successful update, the user data is also
    updated in the Redis cache for faster future retrieval.

    Args:
        user_id (str): The unique identifier of the user to update.
        user_update (UserUpdateRequest): The fields to update for the user.
        request (Request): The FastAPI request object, used for logging request ID.

    Returns:
        UserResponse: The updated user's information.

    Raises:
        HTTPException (404): If no user exists with the given `user_id`.
        HTTPException (400): If provided update data is invalid.
        HTTPException (500): If an unexpected error occurs during the update or cache operation.

    Notes:
        - Only the fields present in the payload are updated; unspecified fields remain unchanged.
        - After updating the database, the user's data is refreshed in the Redis cache.
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
    Delete a user by their unique ID.

    This endpoint removes the user identified by `user_id` from the database.
    On successful deletion, it also removes the user from the Redis cache. The
    response returns a 204 No Content status. If no user exists with the given ID,
    a 404 Not Found error is raised.

    Args:
        user_id (str): The unique identifier of the user to delete.
        request (Request): The FastAPI request object, used for logging request ID.

    Returns:
        None: The response contains no content on successful deletion.

    Raises:
        HTTPException (404): If no user exists with the given `user_id`.
        HTTPException (500): If an unexpected error occurs during deletion or cache removal.

    Notes:
        - After deletion from the database, the corresponding Redis cache entry is removed.
        - This operation is idempotent: deleting a non-existent user results in a 404 error.
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
