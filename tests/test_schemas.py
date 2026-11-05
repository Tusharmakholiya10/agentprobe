"""Schema validation tests."""

import pytest
from pydantic import ValidationError

from agentprobe.schemas import Attack, Task, ToolCall


def test_task_generates_id() -> None:
    """Tasks receive unique identifiers."""
    assert Task(content="hello").id != Task(content="hello").id


def test_tool_call_rejects_extra_fields() -> None:
    """Strict schemas reject unexpected input."""
    with pytest.raises(ValidationError):
        ToolCall(name="read", unexpected=True)  # type: ignore[call-arg]


def test_attack_schema() -> None:
    """Attack records validate the required seed metadata."""
    attack = Attack(
        id="seed-1", category="injection", severity="high", target="email",
        payload="ignore prior instructions", placement="email body",
    )
    assert attack.success_criteria == []
