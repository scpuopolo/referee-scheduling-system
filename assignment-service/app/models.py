from typing import Literal, Optional

from pydantic import BaseModel

HealthStatus = Literal['healthy', 'unhealthy']


class HealthCheckResponse(BaseModel):
    service: str = 'assignment-service'
    status: HealthStatus = 'healthy'
    dependencies: Optional[dict] = None
