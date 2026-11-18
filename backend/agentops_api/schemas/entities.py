from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)

    @field_validator('password')
    @classmethod
    def bcrypt_byte_limit(cls, value: str) -> str:
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be no longer than 72 UTF-8 bytes.')
        return value


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator('password')
    @classmethod
    def bcrypt_byte_limit(cls, value: str) -> str:
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Password must be no longer than 72 UTF-8 bytes.')
        return value


class UserOut(ORMModel):
    id: str
    email: EmailStr
    full_name: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserOut


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default='', max_length=2000)
    environment: str = Field(default='production', max_length=40)
    framework: str = Field(default='custom', max_length=60)


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    environment: str | None = Field(default=None, max_length=40)
    framework: str | None = Field(default=None, max_length=60)
    active: bool | None = None


class AgentOut(ORMModel):
    id: str
    name: str
    description: str
    environment: str
    framework: str
    status: str
    active: bool
    created_at: datetime


class SpanIn(BaseModel):
    span_id: str = Field(max_length=64)
    parent_span_id: str | None = Field(default=None, max_length=64)
    kind: str = Field(default='agent', max_length=20)
    name: str = Field(max_length=160)
    status: str = Field(default='success', max_length=20)
    input: str | None = None
    output: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    latency_ms: float = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)


class TraceIn(BaseModel):
    agent_id: str
    trace_id: str = Field(min_length=8, max_length=64)
    name: str = Field(default='agent.run', max_length=160)
    status: str = Field(default='success', max_length=20)
    input: str | None = None
    output: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    latency_ms: float = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    spans: list[SpanIn] = Field(default_factory=list, max_length=500)


class TraceOut(ORMModel):
    id: str
    agent_id: str
    trace_id: str
    name: str
    status: str
    input: str | None
    output: str | None
    error: str | None
    started_at: datetime
    ended_at: datetime | None
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    metadata_json: dict[str, Any]


class SpanOut(ORMModel):
    id: str
    span_id: str
    parent_span_id: str | None
    kind: str
    name: str
    status: str
    input: str | None
    output: str | None
    error: str | None
    started_at: datetime
    ended_at: datetime | None
    latency_ms: float
    input_tokens: int
    output_tokens: int
    attributes: dict[str, Any]


class DatasetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    description: str = Field(default='', max_length=2000)


class DatasetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=2000)


class CaseCreate(BaseModel):
    input: str = Field(min_length=1, max_length=12000)
    expected_output: str | None = Field(default=None, max_length=12000)
    actual_output: str | None = Field(default=None, max_length=12000)
    reference_context: str | None = Field(default=None, max_length=12000)
    expected_tool: str | None = Field(default=None, max_length=120)
    actual_tool: str | None = Field(default=None, max_length=120)
    instructions: str | None = Field(default=None, max_length=4000)
    structured_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseUpdate(BaseModel):
    input: str | None = Field(default=None, min_length=1, max_length=12000)
    expected_output: str | None = Field(default=None, max_length=12000)
    actual_output: str | None = Field(default=None, max_length=12000)
    reference_context: str | None = Field(default=None, max_length=12000)
    expected_tool: str | None = Field(default=None, max_length=120)
    actual_tool: str | None = Field(default=None, max_length=120)
    instructions: str | None = Field(default=None, max_length=4000)
    structured_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class CaseOut(ORMModel):
    id: str
    dataset_id: str
    input: str
    expected_output: str | None
    actual_output: str | None
    reference_context: str | None
    expected_tool: str | None
    actual_tool: str | None
    instructions: str | None
    structured_schema: dict[str, Any] | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DatasetOut(ORMModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    cases: list[CaseOut] = []


class EvalCreate(BaseModel):
    dataset_id: str
    agent_id: str | None = None
    prompt_version_id: str | None = None
    name: str = Field(min_length=2, max_length=140)
    evaluator: str = Field(default='rules', pattern='^(rules|llm_judge)$')
    metrics: list[str] = Field(default_factory=lambda: ['correctness', 'relevance', 'contextual_accuracy', 'instruction_following', 'hallucination', 'tool_selection', 'structured_output'], max_length=20)


class EvalResultOut(ORMModel):
    id: str
    case_id: str
    score: float
    metrics: dict[str, Any]
    passed: bool
    reasoning: str


class EvalOut(ORMModel):
    id: str
    dataset_id: str
    agent_id: str | None
    prompt_version_id: str | None
    name: str
    status: str
    progress: int
    completed_cases: int
    total_cases: int
    average_score: float
    metrics: dict[str, Any]
    error: str | None
    created_at: datetime
    results: list[EvalResultOut] = []


class PromptCreate(BaseModel):
    agent_id: str
    label: str = Field(min_length=2, max_length=120)
    content: str = Field(min_length=1, max_length=20000)
    notes: str = Field(default='', max_length=2000)
    regression_threshold: float = Field(default=0.05, ge=0, le=1)


class PromptOut(ORMModel):
    id: str
    agent_id: str
    version: int
    label: str
    content: str
    notes: str
    regression_threshold: float
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class SettingsUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    cost_input_per_1k: float | None = Field(default=None, ge=0, le=100)
    cost_output_per_1k: float | None = Field(default=None, ge=0, le=100)
    evaluation_threshold: float | None = Field(default=None, ge=0, le=1)
