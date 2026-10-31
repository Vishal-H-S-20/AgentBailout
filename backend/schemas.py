from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Literal
from decimal import Decimal

Operation = Literal['research','format','summarize','plan','code','validate','extract','transform','review']
Scenario = Literal['normal','crash','heartbeat_loss','timeout','invalid_output','tool_failure','backup_failure','shared_failure','expensive','insufficient_budget','no_backup','exhausted']


class StageDefinition(BaseModel):
    name: str = Field(min_length=1,max_length=80)
    operation: Operation
    agent_id: str = Field(min_length=1,max_length=80)
    version: int = Field(default=1,ge=1)


class AgentRef(BaseModel):
    agent_id: str
    version: int = Field(default=1,ge=1)


class FaultDefinition(BaseModel):
    scenario: Scenario = 'normal'
    stage_index: int | None = Field(default=None,ge=0,le=7)


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1,max_length=80)
    stages: list[StageDefinition] = Field(min_length=1,max_length=8)


class AgentCreate(BaseModel):
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    name: str = Field(min_length=1,max_length=80)
    provider: Literal['offline','openai'] = 'offline'
    model: str = Field(default='deterministic-v1',min_length=1,max_length=120)
    system_instructions: str = Field(default='Perform the stage and return the declared JSON structure.',min_length=1,max_length=4000)
    capabilities: list[Operation] = Field(min_length=1,max_length=9)
    required_tools: list[str] = Field(default_factory=list,max_length=10)
    estimated_cost: Decimal = Field(default=Decimal('0.25'),ge=0,le=100,decimal_places=2)
    estimated_latency: float = Field(default=.1,ge=.01,le=120,allow_inf_nan=False)
    reliability_prior: Decimal = Field(default=Decimal('.95'),ge=0,le=1)
    available: bool = True

    @model_validator(mode='after')
    def real_model_required(self):
        if self.provider=='openai' and self.model=='deterministic-v1':
            raise ValueError('Choose an actual provider model identifier for an external agent')
        return self

    @field_validator('model','system_instructions','name')
    @classmethod
    def no_credentials(cls, value: str) -> str:
        if 'sk-' in value or 'Bearer ' in value:
            raise ValueError('Credentials must be supplied through environment variables only')
        return value


class TaskCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    workflow_id: str = 'template-research'
    stages: list[StageDefinition] | None = Field(default=None,min_length=1,max_length=8)
    recovery_pool: list[AgentRef] = Field(default_factory=lambda:[AgentRef(agent_id='recovery-general'),AgentRef(agent_id='recovery-document'),AgentRef(agent_id='recovery-coding')],max_length=10)
    agentbailout_enabled: bool = True
    failure: FaultDefinition = Field(default_factory=FaultDefinition)
    max_attempts: int = Field(default=1,ge=1,le=3)
    recovery_budget: Decimal = Field(default=Decimal('1.00'),ge=0,le=4,decimal_places=2)
    stage_timeout: float = Field(default=10,ge=.1,le=120,allow_inf_nan=False)
    heartbeat_timeout: float = Field(default=3,ge=.1,le=30,allow_inf_nan=False)

    @field_validator('recovery_pool')
    @classmethod
    def unique_candidates(cls, values: list[AgentRef]) -> list[AgentRef]:
        if len({(r.agent_id,r.version) for r in values}) != len(values):
            raise ValueError('Recovery pool must not contain duplicate agent versions')
        return values

    @field_validator('prompt')
    @classmethod
    def meaningful_prompt(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('Prompt must contain text')
        return value.strip()


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
