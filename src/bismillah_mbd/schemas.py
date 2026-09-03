from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime


class TaskUpdate(BaseModel):
    assignee_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "URGENT"] | None = None
    deadline: date | None = None


class TaskResponse(BaseModel):
    id: int
    milestone_id: int
    assignee_id: int | None
    name: str
    description: str | None
    priority: str
    status: str
    deadline: date
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    assignee_id: int | None = None
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "URGENT"] = "LOW"
    deadline: date


ProjectStatus = Literal["PLANNED", "ACTIVE", "COMPLETED", "CANCELLED"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    start_date: date
    deadline: date
    status: ProjectStatus = "PLANNED"


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    start_date: date | None = None
    deadline: date | None = None
    status: ProjectStatus | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    start_date: date
    deadline: date
    status: str
    created_at: datetime
    updated_at: datetime


MilestoneStatus = Literal["PENDING", "IN_PROGRESS", "COMPLETED"]


class MilestoneInline(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    deadline: date
    status: MilestoneStatus = "PENDING"


class ProjectWithMilestoneCreate(ProjectCreate):
    milestone: MilestoneInline


class MilestoneCreate(BaseModel):
    project_id: int
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    deadline: date
    status: MilestoneStatus = "PENDING"


class MilestoneCreateNoProject(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    deadline: date
    status: MilestoneStatus = "PENDING"


class MilestoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    deadline: date | None = None
    status: MilestoneStatus | None = None


class MilestoneResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: str | None
    deadline: date
    status: str
    created_at: datetime
    updated_at: datetime


class MilestoneWithTasksResponse(MilestoneResponse):
    tasks: list[TaskResponse] = []


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    start_date: date
    deadline: date
    status: str
    created_at: datetime
    updated_at: datetime


class ProjectWithMilestonesResponse(ProjectResponse):
    milestones: list[MilestoneResponse] = []