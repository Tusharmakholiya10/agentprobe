"""SQLite tracer integration tests."""

from agentprobe.schemas import TraceEventType
from agentprobe.tracer import SQLiteTracer


def test_trace_round_trip_and_replay(tmp_path) -> None:
    """A sample trace survives persistence and can be replayed."""
    tracer = SQLiteTracer(tmp_path / "trace.sqlite3")
    run_id = tracer.start_run("system", "task")
    tracer.add_event(
        run_id,
        TraceEventType.TOOL_CALL,
        {"name": "lookup_fake", "arguments": {"item": "fixture"}},
    )
    tracer.add_event(
        run_id,
        TraceEventType.TOOL_RESULT,
        {"tool_call_id": "call-1", "output": "synthetic result"},
    )
    tracer.finish_run(run_id, "done")
    trace = tracer.get_trace(run_id)
    assert trace.final_answer == "done"
    assert [event.event_type for event in trace.events] == [
        TraceEventType.SYSTEM_PROMPT,
        TraceEventType.USER_TASK,
        TraceEventType.TOOL_CALL,
        TraceEventType.TOOL_RESULT,
        TraceEventType.FINAL_ANSWER,
    ]


def test_unknown_run_raises(tmp_path) -> None:
    """Unknown run IDs fail explicitly."""
    import pytest

    tracer = SQLiteTracer(tmp_path / "trace.sqlite3")
    with pytest.raises(KeyError):
        tracer.get_trace("missing")
