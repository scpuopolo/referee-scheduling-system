from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr

HealthStatus = Literal['healthy', 'unhealthy']
UserStatus = Literal['Official', 'Non-Official']


class HealthCheckResponse(BaseModel):
    service: str = 'user-service'
    status: HealthStatus = 'healthy'
    dependencies: Optional[dict] = None


class UserCreateRequest(BaseModel):
    status: UserStatus
    first_name: str
    last_name: str
    username: str
    email: EmailStr


class UserResponse(BaseModel):
    id: str
    status: UserStatus
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime


class UserUpdateRequest(BaseModel):
    status: Optional[UserStatus] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    email: Optional[EmailStr] = None
