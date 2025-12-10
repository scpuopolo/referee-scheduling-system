# Referee Scheduling System

## Description:
A referee management system that keeps track of users, games, and assignments through independent services to demonstrate service boundaries, container orchestration, health monitoring, and maintainability.

## Architecture Overview:

The system is composed of three primary FastAPI microservices:

| Service | Description |
|----------|--------------|
| **User Service** | Manages user profiles and information |
| **Game Service** | Stores game information i.e. times, teams, locations |
| **Assignment Service** | Coordinates referee assignments and reports |

Find the full System Architecture Document [here](./SYSTEM_ARCHITECTURE.md).

## Prerequisites:
- Docker
- Docker Compose
- Python 3.11+

## Installation and Setup:
1. Clone the Repository
    ```bash
    git clone https://github.com/scpuopolo/referee-scheduling-system.git
    cd referee-scheduling-system
    ```
1. Build and Run Containers
    ```bash
    docker compose up -d --build
    ```
1. Verify Running Containers
    ```bash
    docker compose ps
    ```
1. To Bring it All Down After Use
    ```bash
    docker compose down
    ```

## Usage Instructions:
### Access from the Command Line
1. To start, follow the instructions from the [Installation and Setup](#installation-and-setup) section.
1. You can easily check the health of all endpoints by checking the **STATUS** column after running `docker compose ps` in the terminal.
1. To access the `/health` endpoint of the **User Service** directly and neatly print it:
    ```bash
    docker compose exec user-service curl http://localhost:8000/health | jq
    ```
1. To access the `/health` endpoint of the **Game Service** directly and neatly print it:
    ```bash
    docker compose exec game-service curl http://localhost:8000/health | jq
    ```
1. To access the `/health` endpoint of the **Assignment Service** directly and neatly print it:
    ```bash
    docker compose exec assignment-service curl http://localhost:8000/health | jq
    ```
### Access from a Local Machine Browser
1. Open a browser and navigate to a new tab.
1. To access the `/health` endpoint of the **User Service**, go to http://localhost:8001/health
1. To access the `/health` endpoint of the **Game Service**, go to http://localhost:8002/health
1. To access the `/health` endpoint of the **Assignment Service**, go to http://localhost:8003/health

## API Documentation:
### User Service
- `GET /health` $\rightarrow$ liveness check

    **Example Request:** `http://localhost:8001/health`

    **Healthy Response (HTTP 200)**
    ```json
    {
        "service": "user-service",
        "status": "healthy",
        "dependencies": null
    }
    ```

- `POST /users` $\rightarrow$ create a new user

    **Example Request:** `POST http://localhost:8001/users`

    **Request Body**
    ```json
    {
        "status": "Official",
        "first_name": "fname",
        "last_name": "lname",
        "username": "example",
        "email": "fname@example.com"
    }
    ```

    **Success Response (HTTP 201)**
    ```json
    {
        "id": "generated-uuid",
        "status": "Official",
        "first_name": "fname",
        "last_name": "lname",
        "username": "example",
        "email": "fname@example.com",
        "created_at": "2025-01-01T12:00:00",
        "updated_at": "2025-01-01T12:00:00"
    }
    ```

    **Error Responses**
    - HTTP 400 - Missing or invalid fields
        ```json
        { "detail": "Missing first name" }
        ```
    - HTTP 409 - Duplicate username/email
        ```json
        { "detail": "Duplicate username or email"}
        ```
    - HTTP 503 - Database connection issues
        ```json
        { "detail": "Database connection error" }
        ```
    
- `GET /users/{user_id}` $\rightarrow$ Retrieve users with optional filtering

    Retrieve users matching any combination of filter criteria.
    All query params are optional. If non are supplied, all users may be returned.

    **Query Parameters (all optional):**
    - `user_id`: Filter by user ID
    - `status`: Filter by user status (e.g., Official, Non-Official)
    - `username`: Filter by username (min 1 char, max 100)
    - `email`: Filter by email (min 5 chars, max 255)

    **Example Requests:** 
    - Get all users
        
        `GET http://localhost:8001/users`
    - Filter by status:

        `GET http://localhost:8001/users?status=Official`
    - Filter by multiple fields:

        `GET http://localhost:8001/users?username=example&email=fname@example.com`

    **Success Response (HTTP 200)**
    ```json
    {
        "id": "28c45e98-f2f9-4f5d-a981-68c0e1cb4a91",
        "status": "Official",
        "first_name": "fname",
        "last_name": "lname",
        "username": "example",
        "email": "fname@example.com",
        "created_at": "2025-01-01T12:00:00",
        "updated_at": "2025-01-01T12:00:00"
    }
    ```

    **Error Response (HTTP 404)**
    ```json
    { "detail": "No user found with ID: 28c45e98-f2f9-4f5d-a981-68c0e1cb4a91" }
    ```

- `PUT /users/{user_id}` $\rightarrow$ Update user details
    
    **Example Request:** `PUT http://localhost:8001/users/28c45e98-f2f9-4f5d-a981-68c0e1cb4a91`

    **Request Body (partial fields allowed)**
    ```json
    {
        "first_name": "fname_2",
        "last_name": "lname_2"
    }
    ```

    **Success Response (HTTP 200)**
    ```json
    {
        "id": "28c45e98-f2f9-4f5d-a981-68c0e1cb4a91",
        "status": "Official",
        "first_name": "fname_2",
        "last_name": "lname_2",
        "username": "example",
        "email": "fname@example.com",
        "created_at": "2025-01-01T12:00:00",
        "updated_at": "2025-01-01T12:00:00"
    }
    ```

    **Error Response (HTTP 404)**
    ```json
    {
        "detail": "No user found with ID: 28c45e98-f2f9-4f5d-a981-68c0e1cb4a91"
    }
    ```

- `DELETE /users/{uder_id}` $\rightarrow$ Delete a user by ID

    **Example Request:** `DELETE http://localhost:8001/users/28c45e98-f2f9-4f5d-a981-68c0e1cb4a91`

    **Success Response (HTTP 204)**

    *No content returned*

    **Error Response (HTTP 404)**
    ```json
    {
        "detail": "No user found with ID: 28c45e98-f2f9-4f5d-a981-68c0e1cb4a91"
    }
    ```

### Game Service
- `GET /health` $\rightarrow$ liveness check

    **Example Request:** `http://localhost:8002/health`

    **Healthy Response (HTTP 200)**
    ```json
    {
        "service": "game-service",
        "status": "healthy",
        "dependencies": null
    }
    ```

### Assignment Service
- `GET /health` $\rightarrow$ liveness check

    **Example Request:** `http://localhost:8003/health`

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

## Testing:
### Health Endpoints
1. Build and Run Containers
    ```bash
    docker compose up -d --build
    ```
1. Verify Running Containers with Healthy Statuses
    ```bash
    docker compose ps
    ```
1. Verify Each Service's Endpoints Return Correct Responses
    ### User Service:
    In the command line, enter:
    ```bash
    docker compose exec user-service curl http://localhost:8000/health | jq
    ```
    Verify it returns:
    ```json
    {
        "service": "user-service",
        "status": "healthy",
        "dependencies": null
    }
    ```
    ### Game Service:
    In the command line, enter:
    ```bash
    docker compose exec game-service curl http://localhost:8000/health | jq
    ```
    Verify it returns:
    ```json
    {
        "service": "game-service",
        "status": "healthy",
        "dependencies": null
    }
    ```
    ### Assignment Service:
    In the command line, enter:
    ```bash
    docker compose exec assignment-service curl http://localhost:8000/health | jq
    ```
    Verify it returns:
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
    Then, In the command line, enter:
    ```bash
    docker compose down user-service
    ```
    Re-enter:
    ```bash
    docker compose exec assignment-service curl http://localhost:8000/health | jq
    ```
    The response should now be:
    ```json
    {
        "service": "assignment-service",
        "status": "unhealthy",
        "dependencies": {
            "user-service": {"status": "unhealthy", "response_time_ms": 3307.45},
            "game-service": {"status": "healthy", "response_time_ms": 5.6}
        }
    }
    ```
    Again, in the command line, enter:
    ```bash
    docker compose down game-service
    ```
    Again re-enter:
    ```bash
    docker compose exec assignment-service curl http://localhost:8000/health | jq
    ```
    The response this time should be:
    ```json
    {
        "service": "assignment-service",
        "status": "unhealthy",
        "dependencies": {
            "user-service": {"status": "unhealthy", "response_time_ms": 3307.45},
            "game-service": {"status": "unhealthy", "response_time_ms": 4021.82}
        }
    }
    ```
    Then, use the command line to bring the Game Service back:
    ```bash
    docker compose up -d game-service
    ```
    If you again enter:
    ```bash
    docker compose exec assignment-service curl http://localhost:8000/health | jq
    ```
    The final response should depict:
    ```json
    {
        "service": "assignment-service",
        "status": "unhealthy",
        "dependencies": {
            "user-service": {"status": "healthy", "response_time_ms": 3.7},
            "game-service": {"status": "unhealthy", "response_time_ms": 4021.82}
        }
    }
    ```
## Project Structure:
The repository is organized into separate service directories, deployment configuration, and documentation files. Each service follows the same internal pattern for clarity and maintainability.
```bash
.
├── architecture-diagram.png        # High-level visual of the system architecture
├── assignment-service/             # Assignment Service (coordinates assignments)
│ ├── app/
│ │ ├── main.py                     # FastAPI application entrypoint
│ │ └── models.py                   # Pydantic models for this service
│ ├── Dockerfile                    # Build instructions for Assignment Service container
│ └── requirements.txt              # Python dependencies
│
├── CODE_PROVENANCE.md              # Documentation of prompts, changes, and provenance
├── docker-compose.yml              # Orchestrates all services and Redis
│
├── game-service/                   # Game Service (stores game data)
│ ├── app/
│ │ ├── main.py
│ │ └── models.py
│ ├── Dockerfile
│ └── requirements.txt
│
├── README.md                       # Top-level documentation and usage guide
├── SYSTEM_ARCHITECTURE.md          # Detailed architecture document
│
└── user-service/                   # User Service (manages referees and assignors)
├── app/
│ ├── main.py
│ └── models.py
├── Dockerfile
└── requirements.txt
```
Each service is isolated and self-contained, making it easy to test, deploy, and scale independently.