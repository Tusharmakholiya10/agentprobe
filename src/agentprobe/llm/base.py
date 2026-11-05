"""LLM provider contracts and common budget accounting."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from time import perf_counter

from agentprobe.schemas import ExperimentConfig


class BudgetExceeded(RuntimeError):
    """Raised before a call when the configured run budget is exhausted."""


@dataclass(frozen=True)
class Usage:
    """Token and estimated-cost accounting for a provider call."""

    input_tokens: int
    output_tokens: int
    latency_ms: float
    estimated_cost_usd: float


@dataclass(frozen=True)
class LLMResponse:
    """Normalized response returned by every provider."""

    text: str
    usage: Usage
    model: str
    provider: str


class LLMProvider(ABC):
    """Provider interface with cumulative token and spend guards."""

    def __init__(
        self,
        model: str,
        budget: ExperimentConfig | None = None,
        input_usd_per_1k: float = 0.0,
        output_usd_per_1k: float = 0.0,
    ) -> None:
        self.model = model
        self.budget = budget or ExperimentConfig()
        self.input_usd_per_1k = input_usd_per_1k
        self.output_usd_per_1k = output_usd_per_1k
        self.total_tokens = 0
        self.total_cost_usd = 0.0

    def _check_budget(self) -> None:
        """Abort before making a request if the cumulative budget is spent."""
        if self.total_tokens >= self.budget.max_tokens:
            raise BudgetExceeded("Maximum token budget reached; run aborted cleanly.")
        if self.total_cost_usd >= self.budget.max_spend_usd:
            raise BudgetExceeded("Maximum spend budget reached; run aborted cleanly.")

    def _usage(self, prompt: str, output: str, started: float) -> Usage:
        """Build normalized usage and update cumulative accounting."""
        input_tokens = self.count_tokens(prompt)
        output_tokens = self.count_tokens(output)
        cost = (
            input_tokens * self.input_usd_per_1k
            + output_tokens * self.output_usd_per_1k
        ) / 1000
        usage = Usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=(perf_counter() - started) * 1000,
            estimated_cost_usd=cost,
        )
        self.total_tokens += input_tokens + output_tokens
        self.total_cost_usd += cost
        if self.total_tokens > self.budget.max_tokens or self.total_cost_usd > self.budget.max_spend_usd:
            raise BudgetExceeded("Call completed but exceeded the configured budget; run aborted.")
        return usage

    @staticmethod
    def count_tokens(text: str) -> int:
        """Conservative dependency-free token estimate for unmetered providers."""
        return max(1, (len(text) + 3) // 4) if text else 0

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Generate a completion from a prompt."""
