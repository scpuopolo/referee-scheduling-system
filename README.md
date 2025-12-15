# Referee Scheduling System

## Description:
A referee management system that keeps track of users, games, and assignments through independent services to demonstrate service boundaries, container orchestration, health monitoring, and maintainability.

## Architecture Overview:

The system is composed of three primary FastAPI microservices:

| Service | Description |
|----------|--------------|
| **User Service** | Manages user profiles and information |
| **Game Service** | Stores game information i.e. times, teams, locations |
| **Assignment Service** | Coordinates referee assignments |

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
1. Add directories for logging in each service
    - Must match the [project structure](#project-structure)

## Usage Instructions:
### Access from the Command Line
1. To start, follow the instructions from the [Installation and Setup](#installation-and-setup) section.
1. You can easily check the health of all endpoints by checking the **STATUS** column after running `docker compose ps` in the terminal.
1. To access the `/health` endpoint of the **User Service** directly and neatly print it:
    ```bash
    curl http://localhost:8080/user-service/health | jq
    ```
1. To access the `/health` endpoint of the **Game Service** directly and neatly print it:
    ```bash
    curl http://localhost:8080/game-service/health | jq
    ```
1. To access the `/health` endpoint of the **Assignment Service** directly and neatly print it:
    ```bash
    curl http://localhost:8080/assignment-service/health | jq
    ```
### Access from a Local Machine Browser
1. Open a browser and navigate to a new tab.
1. To access the `/health` endpoint of the **User Service**, go to http://localhost:8080/user-service/health
1. To access the `/health` endpoint of the **Game Service**, curl http://localhost:8080/game-service/health
1. To access the `/health` endpoint of the **Assignment Service**, go to http://localhost:8080/assignment-service/health

## API Documentation:
### User Service
- `GET /health` $\rightarrow$ liveness check

    **Example Request:** `http://localhost:8080/user-service/health`

    **Healthy Response (HTTP 200)**
    ```json
    {
        "service": "user-service",
        "status": "healthy",
        "dependencies": null
    }
    ```

- `POST /users` $\rightarrow$ create a new user

    **Example Request:** `POST http://localhost:8080/user-service/users`

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
    
- `GET /users` $\rightarrow$ Retrieve users with optional filtering

    Retrieve users matching any combination of filter criteria.
    All query params are optional. If none are supplied, all users may be returned.

    **Query Parameters (all optional):**
    - `user_id`: Filter by user ID
    - `status`: Filter by user status (e.g., Official, Non-Official)
    - `username`: Filter by username (min 1 char, max 100)
    - `email`: Filter by email (min 5 chars, max 255)

    **Example Requests:** 
    - Get all users
        
        `GET http://localhost:8080/user-service/users`
    - Filter by status:

        `GET http://localhost:8080/user-service/users?status=Official`
    - Filter by multiple fields:

        `GET http://localhost:8080/user-service/users?username=example&email=fname@example.com`

    **Success Response (HTTP 200)**
    ```json
    [
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
    ]
    ```

    **Error Response (HTTP 404)**
    ```json
    { "detail": "No user found with ID: 28c45e98-f2f9-4f5d-a981-68c0e1cb4a91" }
    ```

- `PUT /users/{user_id}` $\rightarrow$ Update user details
    
    **Example Request:** `PUT http://localhost8080/user-service/users/28c45e98-f2f9-4f5d-a981-68c0e1cb4a91`

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

- `DELETE /users/{user_id}` $\rightarrow$ Delete a user by ID

    **Example Request:** `DELETE http://localhost:8080/user-service/users/28c45e98-f2f9-4f5d-a981-68c0e1cb4a91`

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

    **Example Request:** `http://localhost:8080/game-service/health`

    **Healthy Response (HTTP 200)**
    ```json
    {
        "service": "game-service",
        "status": "healthy",
        "dependencies": null
    }
    ```

- `POST /games` $\rightarrow$ create a new game

    **Example Request:** `POST http://localhost:8080/game-service/games`

    **Request Body**
    ```json
    {
        "league": "Recreation Town Soccer",
        "venue": "Main Field",
        "home_team": "Tigers",
        "away_team": "Lions",
        "level": "U18 Boys",
        "halves_length_minutes": 45,
        "scheduled_time": "2025-03-01T14:00:00"
    }
    ```

    **Success Response (HTTP 201)**
    ```json
    {
        "id": "generated-uuid",
        "league": "Recreation Town Soccer",
        "venue": "Main Field",
        "home_team": "Tigers",
        "away_team": "Lions",
        "level": "U18 Boys",
        "halves_length_minutes": 45,
        "game_completed": false,
        "result": null,
        "scheduled_time": "2025-03-01T14:00:00",
        "created_at": "2025-01-01T12:00:00",
        "updated_at": "2025-01-01T12:00:00"
    }
    ```

    **Error Responses**
    - HTTP 400 - Missing or invalid fields
        ```json
        { "detail": "Missing league" }
        ```
    - HTTP 503 - Database connection issues
        ```json
        { "detail": "Database connection error" }
        ```
    
- `GET /games` $\rightarrow$ Retrieve games with optional filtering

    Retrieve games matching any combination of filter criteria.
    All query params are optional. If none are supplied, all games may be returned.

    **Query Parameters (all optional):**
    - `game_id`: Filter by game ID
    - `league`: Filter by league name (min 1 char, max 100)
    - `venue`: Filter by venue name (min 1 char, max 255)
    - `home_team`: Filter by home team name (min 1 char, max 100)
    - `away_team`: Filter by away team name (min 1 char, max 100)
    - `level`: Filter by competition level (min 1 char, max 100)
    - `game_completed`: Filter by completion status (true or false)

    **Example Requests:** 
    - Get all games
        
        `GET http://localhost:8080/game-service/games`
    - Filter by league:

        `GET http://localhost:8080/game-service/games?league=Recreation%20Town%20Soccer`
    - Filter by multiple fields:

        `GET http://localhost:8080/game-service/games?home_team=Tigers&game_completed=false`

    **Success Response (HTTP 200)**
    ```json
    [
        {
            "id": "28c45e98-f2f9-4f5d-a981-68c0e1cb4a91",
            "league": "Recreation Town Soccer",
            "venue": "Main Field",
            "home_team": "Tigers",
            "away_team": "Lions",
            "level": "U18",
            "halves_length_minutes": 45,
            "game_completed": false,
            "result": null,
            "scheduled_time": "2025-03-01T14:00:00",
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:00:00"
        }
    ]
    ```

    **Error Response (HTTP 404)**
    ```json
    { 
        "detail": "No game(s) found with properties: {'league': 'Spring'}" 
    }
    ```

- `PUT /games/{game_id}` $\rightarrow$ Update game details
    
    **Example Request:** `PUT http://localhost:8080/game-service/games/28c45e98-f2f9-4f5d-a981-68c0e1cb4a91`

    **Request Body (partial fields allowed)**
    ```json
    {
        "venue": "Secondary Field",
        "game_completed": true
    }
    ```

    **Success Response (HTTP 200)**
    ```json
    {
        "id": "28c45e98-f2f9-4f5d-a981-68c0e1cb4a91",
        "league": "Recreation Town Soccer",
        "venue": "Secondary Field",
        "home_team": "Tigers",
        "away_team": "Lions",
        "level": "U18 Boys",
        "halves_length_minutes": 45,
        "game_completed": true,
        "result": null,
        "scheduled_time": "2025-03-01T14:00:00",
        "created_at": "2025-01-01T12:00:00",
        "updated_at": "2025-01-02T09:30:00"
    }
    ```

    **Error Response (HTTP 404)**
    ```json
    {
        "detail": "No game found with ID: 28c45e98-f2f9-4f5d-a981-68c0e1cb4a91"
    }
    ```

- `DELETE /games/{game_id}` $\rightarrow$ Delete a game by ID

    **Example Request:** `DELETE http://localhost:8080/game-service/games/28c45e98-f2f9-4f5d-a981-68c0e1cb4a91`

    **Success Response (HTTP 204)**

    *No content returned*

    **Error Response (HTTP 404)**
    ```json
    {
        "detail": "No game found with ID: 28c45e98-f2f9-4f5d-a981-68c0e1cb4a91"
    }
    ```

### Assignment Service
- `GET /health` $\rightarrow$ liveness check

    **Example Request:** `http://localhost:8080/assignment-service/health`

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
- `POST /assignments` $\rightarrow$ create a new assignment

    Creates an assignment for a specific game and optionally assigns referees.
    - Validates that `game_id` exists in the **Game Service**
    - Validates that all referees are **Official** users in the **User Service**

    **Example Request:** `POST http://localhost:8080/assignment-service/assignments`

    **Request Body**
    ```json
    {
        "game_id": "28c45e98-f2f9-4f5d-a981-68c0e1cb4a91",
        "referees": [
            {
                "referee_id": "b91c6b38-9d63-4c6e-a3a0-54a9ef88a9e3",
                "position": "Center"
            },
            {
                "referee_id": "a38d3e9f-44b2-4a58-90cc-1a9d2bfe9021",
                "position": "AR1"
            },
            {
                "referee_id": "e0e91323-d60a-4102-9a99-0ec4ff850aa8",
                "position": "AR2"
            }
        ]
    }
    ```

    **Success Response (HTTP 201)**
    ```json
    {
        "id": "generated-assignment-uuid",
        "game_id": "28c45e98-f2f9-4f5d-a981-68c0e1cb4a91",
        "referees": [
            {
                "referee_id": "b91c6b38-9d63-4c6e-a3a0-54a9ef88a9e3",
                "position": "Center"
            },
            {
                "referee_id": "a38d3e9f-44b2-4a58-90cc-1a9d2bfe9021",
                "position": "AR1"
            },
            {
                "referee_id": "e0e91323-d60a-4102-9a99-0ec4ff850aa8",
                "position": "AR2"
            }
        ],
        "created_at": "2025-01-01T12:00:00",
        "updated_at": "2025-01-01T12:00:00"
    }
    ```

    **Error Responses**
    - HTTP 400 - Missing or invalid fields
        ```json
        { "detail": "Missing game_id" }
        ```
    - HTTP 404 - Game or referee not found
        ```json
        { "detail": "No game(s) found with properties {'game_id': '...'}" }
        ```
    - HTTP 500 - Error communicating with external services
        ```json
        { "detail": "Error communicating with the game service" }
        ```
    - HTTP 503 - Database connection issues
        ```json
        { "detail": "Database connection error" }
        ```
    
- `GET /assignments` $\rightarrow$ Retrieve assignments with optional filtering

    Retrieve assignments matching any combination of filter criteria.
    All query params are optional. If none are supplied, all assignments may be returned.

    **Query Parameters (all optional):**
    - `assignment_id`: Filter by assignment ID
    - `game_id`: Filter by game ID
    - `referee_id`: Filter by referee ID

    **Example Requests:** 
    - Get all assignments
        
        `GET http://localhost:8080/assignment-service/assignments`
    - Filter by game ID:

        `GET http://localhost:8080/assignment-service/assignments?game_id=28c45e98-f2f9-4f5d-a981-68c0e1cb4a91`
    - Filter by referee ID:

        `GET http://localhost:8080/assignment-service/assignments?referee_id=b91c6b38-9d63-4c6e-a3a0-54a9ef88a9e3`

    **Success Response (HTTP 200)**
    ```json
    [
        {
            "id": "assignment-uuid",
            "game_id": "28c45e98-f2f9-4f5d-a981-68c0e1cb4a91",
            "referees": [
                {
                    "referee_id": "b91c6b38-9d63-4c6e-a3a0-54a9ef88a9e3",
                    "position": "Center"
                }
            ],
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:00:00"
        }
    ]
    ```

    **Error Response (HTTP 404)**
    ```json
    { 
        "detail": "No assignment(s) found with properties: {'game_id': '...'}" 
    }
    ```

- `PUT /assignments/{assignment_id}` $\rightarrow$ Update assignment details

    Updates one or more fields of an existing assignment.
    
    Only supplied fields are modified.

    - Referees are revalidated against **User Service**
    - Existing fields remain unchanged if omitted
    
    **Example Request:** `PUT http://localhost:8080/assignment-service/assignments/28c45e98-f2f9-4f5d-a981-68c0e1cb4a91`

    **Request Body (partial fields allowed)**
    ```json
    {
        "referees": [
            {
                "referee_id": "b91c6b38-9d63-4c6e-a3a0-54a9ef88a9e3",
                "position": "Center"
            }
        ]
    }
    ```

    **Success Response (HTTP 200)**
    ```json
    {
        "id": "assignment-uuid",
        "game_id": "28c45e98-f2f9-4f5d-a981-68c0e1cb4a91",
        "referees": [
            {
                "referee_id": "b91c6b38-9d63-4c6e-a3a0-54a9ef88a9e3",
                "position": "Center"
            }
        ],
        "created_at": "2025-01-01T12:00:00",
        "updated_at": "2025-01-02T09:30:00"
    }
    ```

    **Error Responses**
    - HTTP 404 - Not Found
        ```json
        { "detail": "No assignment found with ID: 28c45e98-f2f9-4f5d-a981-68c0e1cb4a91" }
        ```
    - HTTP 500 - Error communicating with external services
        ```json
        { "detail": "Error communicating with the game service" }
        ```
    - HTTP 500 - Error communicating with external services
        ```json
        { "detail": "Error communicating with the game service" }
        ```

- `DELETE /assignments/{assignment_id}` $\rightarrow$ Delete an assignment by ID

    **Example Request:** `DELETE http://localhost:8080/assignment-service/assignments/28c45e98-f2f9-4f5d-a981-68c0e1cb4a91`

    **Success Response (HTTP 204)**

    *No content returned*

    **Error Response (HTTP 404)**
    ```json
    {
        "detail": "No assignment found with ID: 28c45e98-f2f9-4f5d-a981-68c0e1cb4a91"
    }
    ```

- `GET /assignments/full-details/{assignment_id}` $\rightarrow$ retrieve assignment with game & referee details

    Returns an enriched view of an assignment, including:
    - Full game details from the **Game Service**
    - Referee details from the **User Service**, including assignment position

    **Example Request:** `GET http://localhost:8080/assignment-service/assignments/full-details/assignment-uuid`

    **Success Response (HTTP 200)**
    ```json
    {
        "assignment_id": "assignment-uuid",
        "game": {
            "id": "28c45e98-f2f9-4f5d-a981-68c0e1cb4a91",
            "league": "Recreation Town Soccer",
            "venue": "Main Field",
            "home_team": "Tigers",
            "away_team": "Lions",
            "level": "U18 Boys",
            "scheduled_time": "2025-03-01T14:00:00"
        },
        "referees": [
            {
                "id": "28c45e98-f2f9-4f5d-a981-68c0e1cb4a91",
                "status": "Official",
                "first_name": "fname",
                "last_name": "lname",
                "username": "example",
                "email": "fname@example.com",
                "created_at": "2025-01-01T12:00:00",
                "updated_at": "2025-01-01T12:00:00",
                "position": "Center"
            }
        ]
    }
    ```

    **Error Responses**
    - HTTP 404 - Assignment, game, or referee not found
    ```json
    { "detail": "No assignment found with ID: assignment-uuid" }
    ```
    - HTTP 500 - Error communicating with external services
    ```json
    { "detail": "Error communicating with the game service" }
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
The repository is organized as a microservice-based system with clearly separated services, shared infrastructure, and documentation. Each service follows a consistent internal layout to support independent development, testing, and deployment.
```bash
.
├── architecture-diagram.png        # High-level visual overview of system architecture
│
├── assignment-service/             # Assignment Service (manages referee assignments)
│   ├── app/
│   │   ├── logs/
│   │   │   └── assignment_service.txt  # Service runtime logs
│   │   ├── main.py                     # FastAPI application entrypoint
│   │   └── models.py                   # Pydantic request/response models
│   │
│   ├── db/
│   │   ├── 001_schema.sql              # Assignment service database schema
│   │   └── db.py                       # Database connection and queries
│   │
│   ├── Dockerfile                     # Container build configuration
│   └── requirements.txt               # Python dependencies
│
├── game-service/                     # Game Service (stores and manages games)
│   ├── app/
│   │   ├── logs/
│   │   │   └── game_service.txt        # Service runtime logs
│   │   ├── main.py
│   │   └── models.py
│   │
│   ├── db/
│   │   ├── 001_schema.sql              # Game service database schema
│   │   └── db.py
│   │
│   ├── Dockerfile
│   └── requirements.txt
│
├── user-service/                     # User Service (manages referees and assignors)
│   ├── app/
│   │   ├── logs/
│   │   │   └── user_service.txt        # Service runtime logs
│   │   ├── main.py
│   │   └── models.py
│   │
│   ├── db/
│   │   ├── 001_schema.sql              # User service database schema
│   │   └── db.py
│   │
│   ├── Dockerfile
│   └── requirements.txt
│
├── nginx/
│   └── nginx.conf                     # Reverse proxy and API gateway configuration
│
├── docker-compose.yml                # Orchestrates all services and networking
├── README.md                         # Top-level usage and setup instructions
└── SYSTEM_ARCHITECTURE.md            # Detailed system design and service interactions


```
### Design Notes

- Each service is self-contained, with its own API, database schema, and container.

- nginx provides a single external entry point and routes requests to backend services.

- Logs are kept per service to simplify debugging in Dockerized environments.

- The structure supports independent scaling and deployment of services.