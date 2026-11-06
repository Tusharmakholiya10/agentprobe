
"""Pydantic schemas shared across AgentProbe modules."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


class StrictModel(BaseModel):
    """Base model that rejects unknown fields and validates assignments."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Task(StrictModel):
    """A user task supplied to an agent."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    content: str
    created_at: datetime = Field(default_factory=utc_now)


class Tool(StrictModel):
    """A tool declaration exposed to an agent."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolCall(StrictModel):
    """A recorded tool invocation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(StrictModel):
    """The result returned by a tool."""

    tool_call_id: str
    output: Any = None
    error: str | None = None


class TraceEventType(StrEnum):
    """Kinds of events persisted in a trace."""

    SYSTEM_PROMPT = "system_prompt"
    USER_TASK = "user_task"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    FINAL_ANSWER = "final_answer"
    LLM_CALL = "llm_call"
    RUN_ABORTED = "run_aborted"


class TraceEvent(StrictModel):
    """One chronological event in an agent run."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    event_type: TraceEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0


class Trace(StrictModel):
    """Complete trace for a single agent run."""

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    system_prompt: str
    user_task: str
    events: list[TraceEvent] = Field(default_factory=list)
    final_answer: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0


class RunResult(StrictModel):
    """Outcome and accounting summary for one run."""

    run_id: str
    final_answer: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0


class Attack(StrictModel):
    """Attack case schema, introduced now for stable cross-phase typing."""

    id: str
    category: str
    severity: str
    target: str
    payload: str
    placement: str
    success_criteria: list[str] = Field(default_factory=list)


class Verdict(StrictModel):
    """Judge outcome for an attack case."""

    success: bool
    reason: str
    evidence: list[str] = Field(default_factory=list)


class ExperimentConfig(StrictModel):
    """Budget and run configuration shared by later experiment components."""

    name: str = "default"
    max_tokens: int = 100_000
    max_spend_usd: float = 1.0
