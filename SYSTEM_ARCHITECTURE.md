# System Architecture Document

## System Purpose:
The **Referee Scheduling System** allows referees to input availability and get assigned by assignors to games that are registered by sports organizations.

## Service Boundaries:
### User Service
**Responsibility:** Manages users information such as name, user type, contact info, availability, etc.

**Why Separate:**
- Handles user data independently from other application components.
- Encapsulates registration and authentication logic to avoid coupling with game or assignment workflows.
- Makes it easier to manage personal information and availability updates without affecting scheduling logic.

### Game Service
**Responsibility:** Stores game information including times, teams, locations.

**Why Separate:**
- Keeps all game scheduling data consolidated in one service.
- Allows independent scaling for high volumes of game data.
- Simplifies the ability to update or change game details without impacting user or assignment services.

### Assignment Service
**Responsibility:** Coordinates referee assignments and reports.

**Why Separate:**
- Communicates with both the User and Game services, so it should be decoupled from each to maintain clear service boundaries.
- Keeps assignment records and related logic in one place for easy maintenance.

## Data Flow:
The **Referee Scheduling System** includes health monitoring logic that verifies the operation state of all services. Each service exposes its own `/health` endpoint, and the Assignment Service performs dependency checks to ensure that both the User and Game services are functioning properly.

### Health Check Flow
1. **User Service** and **Game Service** each expose a `\health` endpoint returning a JSON object with their service name and health status.
    ```json
    {
        "service": "user-service",
        "status": "healthy",
        "dependencies": null
    }
    ```
1. **Assignment Service** exposes its own `\health` endpoint and depends on both the User and Game services. When this endpoint is called:
    - It sends asynchronous HTTP requests to the `\health` endpoints of `user-service` and `game-service`.
    - Measures the **response time** (in milliseconds) and collects the **status** of each dependency.
1. The Assignment Service aggregates the results and returns one of two possible outcomes:

    **Healthy Response (HTTP 200)**
    ```json
    {
        "service": "assignment-service",
        "status": "healthy",
        "dependencies": {
            "user-service": {"status": "healthy", "response_time_ms": 5.2},
            "game-service": {"status": "healthy", "response_time_ms": 4.7}
        }
    }
    ```
    **Unhealthy Response (HTTP 503)**
    ```json
    {
        "service": "assignment-service",
        "status": "unhealthy",
        "dependencies": {
            "user-service": {"status": "unhealthy", "response_time_ms": 3056.73},
            "game-service": {"status": "healthy", "response_time_ms": 4.7}
        }
    }
    ```
### Summary Flow
- `user-service` $\rightarrow$ Provides simple static health status.
- `game-service` $\rightarrow$ Provides simple static health status.
- `assignment-service` $\rightarrow$ Dynamically checks dependencies and composes a detailed health report.

## Communication Patterns:
### Services Health Communication
- **Synchronous HTTP Calls** - Utilizes Python's `httpx` library:
    - Assignment $\rightarrow$ User: Assignment calls the User Service's `\health` route to check if it is healthy.
    - Assignment $\rightarrow$ Game: Assignment calls the Game Service's `\health` route to check if it is healthy.

## Technology Stack:
| Component | Technology | Reason |
| ---------- | ---------- | ---------- |
| API Framework | FastAPI | Asynchronous, typed, OpenAPI docs |
| Containerization | Docker + Compose | Isolated, reproducible environments |
| HTTP Client | httpx | Async, configurable retries and timeouts |
| Language | Python 3.11+ | Strong async support and developer familiarity |
| Web Server | Uvicorn | ASGI server optimized for FastAPI |
| Data Modeling / Validation | Pydantic v2 | Automatically enforces consistency and correctness for models and schemas |


