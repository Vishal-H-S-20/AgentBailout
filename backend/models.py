from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    prompt: Mapped[str]
    status: Mapped[str] = mapped_column(default='CREATED')
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(nullable=True)
    stages: Mapped[list['Stage']] = relationship(order_by='Stage.position', cascade='all, delete-orphan')


class Stage(Base):
    __tablename__ = 'stages'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'), index=True)
    worker_id: Mapped[str] = mapped_column(default=lambda: str(uuid4()))
    name: Mapped[str]
    position: Mapped[int]
    status: Mapped[str] = mapped_column(default='PENDING')
    started_at: Mapped[str | None] = mapped_column(nullable=True)
    ended_at: Mapped[str | None] = mapped_column(nullable=True)
    heartbeat_at: Mapped[str | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(nullable=True)
    recovery_attempts: Mapped[int] = mapped_column(default=0)


class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'), index=True)
    timestamp: Mapped[str] = mapped_column(default=now)
    type: Mapped[str] = mapped_column(String(64))
    message: Mapped[str]


class Settlement(Base):
    __tablename__ = 'settlements'
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'), primary_key=True)
    outcome: Mapped[str]
    timestamp: Mapped[str] = mapped_column(default=now)


class LedgerEntry(Base):
    __tablename__ = 'ledger_entries'
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'), index=True)
    reference: Mapped[str]
    event_type: Mapped[str]
    account: Mapped[str]
    debit_cents: Mapped[int]
    credit_cents: Mapped[int]
    description: Mapped[str]
    timestamp: Mapped[str] = mapped_column(default=now)


class Agent(Base):
    __tablename__ = 'agents'
    id: Mapped[str] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(primary_key=True)
    configuration: Mapped[dict] = mapped_column(JSON)
    successes: Mapped[int] = mapped_column(default=0)
    failures: Mapped[int] = mapped_column(default=0)
    timeouts: Mapped[int] = mapped_column(default=0)
    total_seconds: Mapped[float] = mapped_column(default=0)
    recovery_involvement: Mapped[int] = mapped_column(default=0)
    last_execution_at: Mapped[str | None] = mapped_column(nullable=True)


class Workflow(Base):
    __tablename__ = 'workflows'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    definition: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)


class Execution(Base):
    __tablename__ = 'executions'
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'), primary_key=True)
    configuration: Mapped[dict] = mapped_column(JSON)
    started_at: Mapped[str | None] = mapped_column(nullable=True)
    ended_at: Mapped[str | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)


class Attempt(Base):
    __tablename__ = 'attempts'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'), index=True)
    stage_id: Mapped[str] = mapped_column(ForeignKey('stages.id'), index=True)
    agent_id: Mapped[str]
    agent_version: Mapped[int]
    recovery: Mapped[bool]
    status: Mapped[str] = mapped_column(default='RUNNING')
    started_at: Mapped[str] = mapped_column(default=now)
    ended_at: Mapped[str | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    error_category: Mapped[str | None] = mapped_column(nullable=True)
    error_fingerprint: Mapped[str | None] = mapped_column(nullable=True)
    usage: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    api_cost: Mapped[str | None] = mapped_column(nullable=True)
    simulated_cost: Mapped[str] = mapped_column(default='0.00')
    output_valid: Mapped[bool] = mapped_column(default=False)


class Comparison(Base):
    __tablename__ = 'comparisons'
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))
    baseline_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'))
    protected_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'))
    created_at: Mapped[str] = mapped_column(default=now)
