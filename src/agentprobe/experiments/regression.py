import os

from agentprobe.schemas import Trace


class RegressionGenerator:
    """Generates standalone pytest files from recorded traces."""
    
    @staticmethod
    def generate_test(trace: Trace, output_dir: str = "tests/regression") -> str:
        os.makedirs(output_dir, exist_ok=True)
        safe_task_id = "".join([c if c.isalnum() else "_" for c in trace.task.id])
        file_path = os.path.join(output_dir, f"test_regression_{safe_task_id}.py")
        
        # Build the mock responses array based on the trace steps
        mock_responses = []
        expected_calls = []
        
        for step in trace.steps:
            # We assume step.content is the text response from the LLM
            content = step.content or ""
            calls_repr = []
            for call in step.tool_calls:
                calls_repr.append(f"ToolCall(call_id='{call.call_id}', name='{call.name}', arguments={call.arguments})")
                expected_calls.append(call.name)
                
            mock_responses.append(f"({content!r}, [{', '.join(calls_repr)}])")
            
        mock_responses_str = ",\n        ".join(mock_responses)
        expected_calls_str = repr(expected_calls)
        
        # Generate the pytest file content
        code = f"""import pytest
from agentprobe.schemas import ToolCall
from agentprobe.llm.wrapper import MockProvider
from agentprobe.targets.base import BaseTarget
# Note: Import your specific target agent here

def test_regression_{safe_task_id}() -> None:
    \"\"\"Auto-generated regression test for task: {trace.task.id}\"\"\"
    
    # 1. Setup Mock LLM with exact responses from the trace
    mock_responses = [
        {mock_responses_str}
    ]
    provider = MockProvider(mock_responses=mock_responses)
    
    # 2. Setup Agent (Replace BaseTarget with your actual agent class)
    # agent = EmailAgent(llm=provider)
    
    # 3. Assert Expected Tool Calls (Implementation depends on your target's tracking)
    expected_tools = {expected_calls_str}
    
    # Example Assertion:
    # trace = agent.run(task_id="{trace.task.id}", task_desc={trace.task.description!r})
    # executed_tools = [call.name for step in trace.steps for call in step.tool_calls]
    # assert executed_tools == expected_tools
"""
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        return file_path