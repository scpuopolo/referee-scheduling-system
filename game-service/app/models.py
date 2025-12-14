from datetime import datetime
from typing import List, Literal, Optional

# from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, model_validator

HealthStatus = Literal['healthy', 'unhealthy']


class CardInfo(BaseModel):
    type: Literal['Yellow', 'Red']
    team: str = Field(..., min_length=1, max_length=100)
    player_number: int = Field(..., ge=0, le=999)
    minute_given: int = Field(..., ge=0, le=200)
    reason: str = Field(..., min_length=1, max_length=20)


class CompletedGameInfo(BaseModel):
    home_team_score: Optional[int] = Field(None, ge=0, le=99)
    away_team_score: Optional[int] = Field(None, ge=0, le=99)
    cards_issued: List[CardInfo] = []

    """@model_validator(mode="after")
    def validate_scores(self):
        if (self.home_team_score is None) != (self.away_team_score is None):
            raise RequestValidationError(errors=[
                                         {'msg': "Both home_team_score and away_team_score must be provided together."}])
        return self"""


class HealthCheckResponse(BaseModel):
    service: str = 'game-service'
    status: HealthStatus = 'healthy'
    dependencies: Optional[dict] = None


class GameCreateRequest(BaseModel):
    league: str = Field(..., min_length=1, max_length=100)
    venue: str = Field(..., min_length=1, max_length=255)
    home_team: str = Field(..., min_length=1, max_length=100)
    away_team: str = Field(..., min_length=1, max_length=100)
    level: str = Field(..., min_length=1, max_length=100)
    halves_length_minutes: int = Field(default=45, gt=0, lt=46)
    scheduled_time: datetime

    class Config:
        str_strip_whitespace = True


class GameResponse(BaseModel):
    id: str
    league: str
    venue: str
    home_team: str
    away_team: str
    level: str
    halves_length_minutes: int
    game_completed: bool
    result: Optional[CompletedGameInfo] = None
    scheduled_time: datetime
    created_at: datetime
    updated_at: datetime


class GameUpdateRequest(BaseModel):
    league: Optional[str] = Field(default=None, min_length=1, max_length=100)
    venue: Optional[str] = Field(default=None, min_length=1, max_length=255)
    home_team: Optional[str] = Field(
        default=None, min_length=1, max_length=100)
    away_team: Optional[str] = Field(
        default=None, min_length=1, max_length=100)
    level: Optional[str] = Field(default=None, min_length=1, max_length=100)
    halves_length_minutes: Optional[int] = Field(default=None, gt=0, lt=46)
    scheduled_time: Optional[datetime] = None
    game_completed: Optional[bool] = None
    result: Optional[CompletedGameInfo] = None

    class Config:
        str_strip_whitespace = True

    """@model_validator(mode="after")
    def validate_result(self):
        if not self.game_completed and self.result is not None:
            raise RequestValidationError(
                errors=[{"msg": "Only completed games can have result."}])
        return self"""
