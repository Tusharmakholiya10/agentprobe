from agentprobe.llm.wrapper import MockProvider
from agentprobe.schemas import Task, ToolCall, ToolResult, Trace, TraceStep
from agentprobe.tracer.sqlite_tracer import SQLiteTracer


def test_mock_provider():
    provider = MockProvider(
        mock_responses=[
            (
                "Thinking...",
                [ToolCall(call_id="1", name="test_tool", arguments={"a": 1})],
            ),
        ]
    )
    resp, calls, stats = provider.generate("hello", "sys", [])
    assert resp == "Thinking..."
    assert len(calls) == 1
    assert calls[0].name == "test_tool"
    assert stats["cost"] == 0.0001


def test_tracer_and_replay(tmp_path):
    db_path = str(tmp_path / "test.db")
    tracer = SQLiteTracer(db_path)

    trace = Trace(
        run_id="test_run_123",
        system_prompt="You are a helpful agent.",
        task=Task(id="t1", description="Do a thing"),
        steps=[
            TraceStep(
                step_num=1,
                content="I will call a tool",
                tool_calls=[ToolCall(call_id="c1", name="my_tool", arguments={})],
                tool_results=[ToolResult(call_id="c1", result="Success")],
            )
        ],
        final_answer="Done",
        total_cost=0.01,
        total_tokens=100,
    )

    tracer.save_trace(trace)

    loaded = tracer.get_trace("test_run_123")
    assert loaded.run_id == "test_run_123"
    assert len(loaded.steps) == 1
    assert loaded.steps[0].tool_calls[0].name == "my_tool"
