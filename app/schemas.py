from datetime import datetime
from pydantic import BaseModel

class TaskResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    priority: str
    completed: bool
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime

class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str | None = "medium"
    completed: bool | None = False
    due_date: datetime | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    completed: bool | None = None
    due_date: datetime | None = None

#registration

class UserCreate(BaseModel):
    email: str
    password: str

#login

class UserLogin(BaseModel):
    email: str
    password: str

#JWT

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

#logout

class LogoutRequest(BaseModel):
    refresh_token: str