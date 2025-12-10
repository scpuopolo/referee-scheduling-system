from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

HealthStatus = Literal['healthy', 'unhealthy']
UserStatus = Literal['Official', 'Non-Official']


class HealthCheckResponse(BaseModel):
    service: str = 'user-service'
    status: HealthStatus = 'healthy'
    dependencies: Optional[dict] = None


class UserCreateRequest(BaseModel):
    status: UserStatus
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=1, max_length=100)
    email: EmailStr = Field(..., min_length=5, max_length=255)


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
    first_name: Optional[str] = Field(
        default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(
        default=None, min_length=1, max_length=100)
    username: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[EmailStr] = Field(
        default=None, min_length=5, max_length=255)
