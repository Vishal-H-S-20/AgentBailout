from pydantic import BaseModel, ConfigDict, Field


class TaskCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)


class StageView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    task_id: str
    worker_id: str
    name: str
    position: int
    status: str
    started_at: str | None
    ended_at: str | None
    heartbeat_at: str | None
    duration_seconds: float | None
    input: dict | None
    result: dict | None
    error: str | None
    recovery_attempts: int


class TaskView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    prompt: str
    status: str
    created_at: str
    updated_at: str
    result: dict | None
    error: str | None
    stages: list[StageView]


class EventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_id: str
    timestamp: str
    type: str
    message: str
