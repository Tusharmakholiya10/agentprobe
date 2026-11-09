import os
from pathlib import Path

from agentprobe.experiments.regression import RegressionGenerator
from agentprobe.schemas import Task, ToolCall, Trace, TraceStep


def test_regression_generator(tmp_path: Path) -> None:
    # 1. Create a dummy trace
    trace = Trace(
        run_id="r1",
        system_prompt="sys",
        task=Task(id="task_123", description="Send an email"),
        final_answer="Done",
        steps=[
            TraceStep(
                step_num=1,
                content="I will send it.",
                tool_calls=[ToolCall(call_id="c1", name="send_email", arguments={"to": "admin"})]
            )
        ]
    )
    
    # 2. Generate the test file
    out_dir = str(tmp_path / "regression")
    file_path = RegressionGenerator.generate_test(trace, output_dir=out_dir)
    
    # 3. Verify the file exists and contains the correct Python code
    assert os.path.exists(file_path)
    
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    assert "def test_regression_task_123() -> None:" in code
    assert "send_email" in code
    assert "['send_email']" in code # The expected_tools array
    assert "I will send it." in code # The mocked content