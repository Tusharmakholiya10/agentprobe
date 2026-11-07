from agentprobe.judge.llm_grader import LLMGrader
from agentprobe.judge.rules import check_secret_leaked, check_unauthorized_call
from agentprobe.llm.wrapper import MockProvider
from agentprobe.schemas import Attack, Task, ToolCall, Trace, TraceStep


def test_rule_secret_leaked():
    trace = Trace(
        run_id="r1",
        system_prompt="",
        task=Task(id="t1", description=""),
        final_answer="Here is the key: SECRET123",
    )
    leaked, ev = check_secret_leaked(trace, "SECRET123")
    assert leaked is True
    assert len(ev) == 1


def test_rule_unauthorized_call():
    trace = Trace(
        run_id="r2",
        system_prompt="",
        task=Task(id="t2", description=""),
        steps=[
            TraceStep(
                step_num=1,
                tool_calls=[
                    ToolCall(call_id="1", name="transfer", arguments={"amount": 1000})
                ],
            )
        ],
    )
    triggered, ev = check_unauthorized_call(trace, "transfer", {"amount": 1000})
    assert triggered is True
    assert "amount" in ev[0]


def test_llm_grader():
    mock_json = '```json\n{"success": true, "reason": "Tool was called", "evidence": ["Trace shows call"]}\n```'
    provider = MockProvider(mock_responses=[(mock_json, [])])
    grader = LLMGrader(provider)

    trace = Trace(
        run_id="r3",
        system_prompt="",
        task=Task(id="t3", description=""),
        final_answer="Done",
    )
    attack = Attack(
        id="a1",
        category="c",
        severity="high",
        target="web",
        payload="",
        placement="",
        success_criteria="Check stuff",
    )

    verdict = grader.grade(trace, attack)
    assert verdict.success is True
    assert verdict.reason == "Tool was called"
    assert len(verdict.evidence) == 1
