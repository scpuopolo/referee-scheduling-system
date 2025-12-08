import os
from contextlib import asynccontextmanager

from app.models import (HealthCheckResponse, UserCreateRequest, UserResponse,
                        UserUpdateRequest)
from db.db import (close_db_connection, create_user_in_db, delete_user_from_db,
                   get_user_from_db, init_db, update_user_in_db)
from fastapi import FastAPI, HTTPException

PG_DSN = os.getenv("PG_DSN")


# TODO: Add logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    close_db_connection()

app = FastAPI(lifespan=lifespan)


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
def create_user(user: UserCreateRequest):
    """
    Endpoint to create a new user.

    returns status 201 on successful creation of a user.
    """
    # Input validation
    if not user.status or user.status not in ['Official', 'Non-Official']:
        raise HTTPException(
            status_code=400, detail="Missing or invalid user status")
    if not user.first_name:
        raise HTTPException(status_code=400, detail="Missing first name")
    if not user.last_name:
        raise HTTPException(status_code=400, detail="Missing last name")
    if not user.username:
        raise HTTPException(status_code=400, detail="Missing username")
    if not user.email:
        raise HTTPException(status_code=400, detail="Missing email")

    # Add user to database
    try:
        # TODO: Implement create_user_in_db function
        new_user = create_user_in_db(user)

        if not new_user:
            raise HTTPException(
                status_code=500, detail="Failed to create user")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error while creating user: {e}")

    return new_user


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str):
    """
    Endpoint to get user details by user ID.

    returns status 200 on successful retrieval of user details.
    """
    try:
        # TODO: Implement get_user_from_db function
        user = get_user_from_db(user_id)

        if not user:
            raise HTTPException(
                status_code=404, detail=f"No user found with ID: {user_id}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error while retrieving user: {e}")

    return user


@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: str, user_update: UserUpdateRequest):
    """
    Endpoint to update user details by user ID.

    returns status 200 on successful update of user details.
    """
    try:
        # TODO: Implement update_user_in_db function
        updated_user = update_user_in_db(user_id, user_update)

        if not updated_user:
            raise HTTPException(
                status_code=404, detail=f"No user found with ID: {user_id}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error while updating user: {e}")

    return updated_user


@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: str):
    """
    Endpoint to delete a user by user ID.

    returns status 204 on successful deletion of the user.
    """
    try:
        # TODO: Implement delete_user_from_db function
        deleted = delete_user_from_db(user_id)

        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"No user found with ID: {user_id}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error while deleting user: {e}")
