import os
from datetime import datetime, timezone

import httpx
from app.models import HealthCheckResponse
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

# External service bases
USER_SERVICE_BASE = os.getenv("USER_SERVICE_BASE", "http://user-service:8000")
GAME_SERVICE_BASE = os.getenv("GAME_SERVICE_BASE", "http://game-service:8000")


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
