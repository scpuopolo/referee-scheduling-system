from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

HealthStatus = Literal['healthy', 'unhealthy']
Position = Literal['Center', 'AR1', 'AR2',
                   'Fourth', 'VAR', 'AVAR', 'AAR1', 'AAR2']


class HealthCheckResponse(BaseModel):
    service: str = 'assignment-service'
    status: HealthStatus = 'healthy'
    dependencies: Optional[dict] = None


class Referee(BaseModel):
    referee_id: str
    position: Position


class AssignmentCreateRequest(BaseModel):
    game_id: str = Field(...)
    referees: Optional[List[Referee]] = Field(default=None)


class AssignmentResponse(BaseModel):
    id: str
    referees: Optional[List[Referee]]
    game_id: str
    assigned_at: datetime
    updated_at: datetime


class AssignmentUpdateRequest(BaseModel):
    referees: List[Referee] = Field(...)
