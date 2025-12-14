-- Schema for Game Service
CREATE TABLE IF NOT EXISTS games (
    id CHAR(36) PRIMARY KEY,
    league VARCHAR(100) NOT NULL,
    venue VARCHAR(255) NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    level VARCHAR(100) NOT NULL,
    halves_length_minutes INT NOT NULL DEFAULT 45,
    game_completed BOOLEAN NOT NULL DEFAULT FALSE,
    result JSONB,
    scheduled_time TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);