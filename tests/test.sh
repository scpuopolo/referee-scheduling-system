#!/usr/bin/env bash

set -e

GATEWAY="http://localhost:8080"

docker compose down || true
docker compose up -d --build \
  --scale user-service=2 \
  --scale game-service=2 \
  --scale assignment-service=2

until curl -sf "$GATEWAY/assignment-service/health" >/dev/null; do
  sleep 1
done

echo "================================================="
echo " Referee Scheduling System - Full System Test"
echo "================================================="
echo

command -v jq >/dev/null 2>&1 || {
  echo "jq is required but not installed."
  exit 1
}

print_section () {
  echo
  echo "-------------------------------------------------"
  echo " $1"
  echo "-------------------------------------------------"
}

print_section "1. Initial Health Checks"

curl -s "$GATEWAY/user-service/health" | jq
curl -s "$GATEWAY/game-service/health" | jq
curl -s "$GATEWAY/assignment-service/health" | jq

print_section "2. Creating Users (User Service)"

USER_1_JSON=$(curl -s -X POST "$GATEWAY/user-service/users" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "Official",
    "first_name": "Alice",
    "last_name": "Ref",
    "username": "alice_ref",
    "email": "alice@example.com"
  }')

USER_2_JSON=$(curl -s -X POST "$GATEWAY/user-service/users" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "Official",
    "first_name": "Bob",
    "last_name": "Ref",
    "username": "bob_ref",
    "email": "bob@example.com"
  }')

USER_1_ID=$(echo "$USER_1_JSON" | jq -r '.id')
USER_2_ID=$(echo "$USER_2_JSON" | jq -r '.id')

echo "Created Users:"
echo "$USER_1_JSON" | jq
echo "$USER_2_JSON" | jq

print_section "3. Creating Game (Game Service)"

GAME_JSON=$(curl -s -X POST "$GATEWAY/game-service/games" \
  -H "Content-Type: application/json" \
  -d '{
    "league": "Town Soccer League",
    "venue": "Main Field",
    "home_team": "Tigers",
    "away_team": "Lions",
    "level": "U18 Boys",
    "halves_length_minutes": 45,
    "scheduled_time": "2025-03-01T14:00:00"
  }')

GAME_ID=$(echo "$GAME_JSON" | jq -r '.id')

echo "Created Game:"
echo "$GAME_JSON" | jq

print_section "4. Creating Assignment (Cross-Service Validation)"

ASSIGNMENT_JSON=$(curl -s -X POST "$GATEWAY/assignment-service/assignments" \
  -H "Content-Type: application/json" \
  -d "{
    \"game_id\": \"$GAME_ID\",
    \"referees\": [
      { \"referee_id\": \"$USER_1_ID\", \"position\": \"Center\" },
      { \"referee_id\": \"$USER_2_ID\", \"position\": \"AR1\" }
    ]
  }")

ASSIGNMENT_ID=$(echo "$ASSIGNMENT_JSON" | jq -r '.id')

echo "Created Assignment:"
echo "$ASSIGNMENT_JSON" | jq

print_section "5. Enriched Assignment View (Service Aggregation)"

curl -s "$GATEWAY/assignment-service/assignments/full-details/$ASSIGNMENT_ID" | jq

print_section "6. Failure Case: Invalid Referee ID"
curl -s -X POST "$GATEWAY/assignment-service/assignments" \
  -H "Content-Type: application/json" \
  -d "{
    \"game_id\": \"$GAME_ID\",
    \"referees\": [
      { \"referee_id\": \"00000000-0000-0000-0000-000000000000\", \"position\": \"Center\" }
    ]
  }" | jq

print_section "7. Failure Case: Invalid Game ID"

curl -s -X POST "$GATEWAY/assignment-service/assignments" \
  -H "Content-Type: application/json" \
  -d "{
    \"game_id\": \"00000000-0000-0000-0000-000000000000\",
    \"referees\": [
      { \"referee_id\": \"$USER_1_ID\", \"position\": \"Center\" }
    ]
  }" | jq

print_section "8. Failure Case: Dependency Down"

docker compose stop game-service
sleep 2

curl -s "$GATEWAY/assignment-service/health" | jq

echo "Attempting assignment creation with Game Service down:"
curl -s -X POST "$GATEWAY/assignment-service/assignments" \
  -H "Content-Type: application/json" \
  -d "{
    \"game_id\": \"$GAME_ID\",
    \"referees\": [
      { \"referee_id\": \"$USER_1_ID\", \"position\": \"Center\" }
    ]
  }" | jq

docker compose start game-service
sleep 3

print_section "9. Cleanup: Delete Assignment"

curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
  -X DELETE "$GATEWAY/assignment-service/assignments/$ASSIGNMENT_ID"

echo "Verify assignment deletion:"
curl -s "$GATEWAY/assignment-service/assignments?assignment_id=$ASSIGNMENT_ID" | jq

print_section "10. Cleanup: Delete Game"

curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
  -X DELETE "$GATEWAY/game-service/games/$GAME_ID"

echo "Verify game deletion:"
curl -s "$GATEWAY/game-service/games?game_id=$GAME_ID" | jq

print_section "11. Cleanup: Delete Users"

curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
  -X DELETE "$GATEWAY/user-service/users/$USER_1_ID"

curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
  -X DELETE "$GATEWAY/user-service/users/$USER_2_ID"

echo "Verify users deletion:"
curl -s "$GATEWAY/user-service/users?user_id=$USER_1_ID" | jq
curl -s "$GATEWAY/user-service/users?user_id=$USER_2_ID" | jq

print_section "Distributed System Test Complete"

docker compose down