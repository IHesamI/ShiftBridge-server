from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List, Dict, Any
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



class WorkerResponse(BaseModel):
    id: str
    name: str
    role: str
    department: str
    max_hours: float
    current_hours: float
    avatar: Optional[str] = None

    class Config:
        from_attributes = True

class ShiftResponse(BaseModel):
    id: str
    project_id: str
    worker_id: str
    day: str
    type: str
    shift_time: str
    hours: float
    note: Optional[str] = None
    updated_by_ai: bool
    conflict_reason: Optional[str] = None

    class Config:
        from_attributes = True

class ProjectResponse(BaseModel):
    id: str
    manager_id: str
    title: str
    workers: List[WorkerResponse] = []

    class Config:
        from_attributes = True

class ScenarioResponse(BaseModel):
    id: str
    affected_worker_id: str
    affected_worker_name: str
    conflict_day: str
    original_shift: str
    reason: str
    constraint: str
    prompt_text: str

    class Config:
        from_attributes = True

class ChatMessageResponse(BaseModel):
    id: str
    sender: str
    role_name: Optional[str] = None
    text: str
    timestamp: str
    is_pending_approval: Optional[bool] = None
    proposal_id: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    approval_state: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True