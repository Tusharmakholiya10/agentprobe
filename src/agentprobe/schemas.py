from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class Tool(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolCall(BaseModel):
    call_id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    call_id: str
    result: str
    is_error: bool = False


class Task(BaseModel):
    id: str
    description: str


class TraceStep(BaseModel):
    step_num: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    content: str | None = None


class Trace(BaseModel):
    run_id: str
    system_prompt: str
    task: Task
    steps: list[TraceStep] = Field(default_factory=list)
    final_answer: str | None = None
    total_cost: float = 0.0
    total_tokens: int = 0


class Verdict(BaseModel):
    success: bool
    reason: str
    evidence: list[str]


class Attack(BaseModel):
    id: str
    category: str
    severity: str
    target: str
    payload: str
    placement: str
    success_criteria: str


class RunResult(BaseModel):
    run_id: str
    trace: Trace
    verdict: Verdict | None = None


class ExperimentConfig(BaseModel):
    name: str
    budget: float
    models: list[str]
    defenses: list[str]
