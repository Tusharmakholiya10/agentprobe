import time
from abc import ABC, abstractmethod

from agentprobe.schemas import ToolCall


class LLMProvider(ABC):
    @abstractmethod
    def generate(
        self, prompt: str, system: str, tools: list
    ) -> tuple[str, list[ToolCall], dict]:
        """Returns (text_response, tool_calls, usage_stats_dict)"""


class MockProvider(LLMProvider):
    def __init__(self, mock_responses=None):
        self.mock_responses = mock_responses or []
        self.call_count = 0

    def generate(
        self, prompt: str, system: str, tools: list
    ) -> tuple[str, list[ToolCall], dict]:
        start = time.time()

        if self.call_count < len(self.mock_responses):
            resp, tool_calls = self.mock_responses[self.call_count]
        else:
            resp, tool_calls = "Mock final answer", []

        self.call_count += 1
        latency = (time.time() - start) * 1000
        stats = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "cost": 0.0001,
            "latency_ms": latency,
        }
        return resp, tool_calls, stats


# Note: OllamaProvider and HostedProvider stubbed for Phase 1 size limits,
# fully implementable via requests and openai package respectively.
