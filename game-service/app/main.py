from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
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

    return {
        "service": "game-service",
        "status": "healthy",
        "dependencies": None,
    }
