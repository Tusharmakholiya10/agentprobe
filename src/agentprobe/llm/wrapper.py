import time
from abc import ABC, abstractmethod
from typing import Any

from agentprobe.schemas import ToolCall


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system: str, tools: list[dict[str, Any]]) -> tuple[str, list[ToolCall], dict[str, Any]]:
        """Returns (text_response, tool_calls, usage_stats_dict)"""

class MockProvider(LLMProvider):
    def __init__(self, mock_responses: list[tuple[str, list[ToolCall]]] | None = None) -> None:
        self.mock_responses = mock_responses or []
        self.call_count = 0

    def generate(self, prompt: str, system: str, tools: list[dict[str, Any]]) -> tuple[str, list[ToolCall], dict[str, Any]]:
        start = time.time()
        
        if self.call_count < len(self.mock_responses):
            resp, tool_calls = self.mock_responses[self.call_count]
        else:
            resp, tool_calls = "Mock final answer", []
            
        self.call_count += 1
        latency = (time.time() - start) * 1000
        stats = {"prompt_tokens": 10, "completion_tokens": 20, "cost": 0.0001, "latency_ms": latency}
        return resp, tool_calls, stats