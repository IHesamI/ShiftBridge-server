from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    # Updated for Pydantic V2
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class ShiftBase(BaseModel):
    project_id: int
    owner_id: int
    start_date: datetime
    length: int

class ShiftCreate(ShiftBase):
    pass

class ShiftResponse(ShiftBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ProjectBase(BaseModel):
    manager_id: int
    title: str

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: int
    created_at: Optional[datetime] = None
    workers: list[UserResponse] = []
    shifts: list[ShiftResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatMessage]] = None

class ChatResponse(BaseModel):
    reply: str
    tools_used: list[dict] = []
    updated_shift: Optional[dict] = None

class ToolExecutionRequest(BaseModel):
    tool_name: str
    arguments: dict = {}

class ToolExecutionResponse(BaseModel):
    success: bool
    result: dict

class RescheduleRequest(BaseModel):
    new_start_date: str
    new_length: Optional[int] = None