"""Environment-driven provider construction."""

import os

from agentprobe.llm.base import LLMProvider
from agentprobe.llm.hosted import HostedProvider
from agentprobe.llm.mock import MockProvider
from agentprobe.llm.ollama import OllamaProvider
from agentprobe.schemas import ExperimentConfig


def create_provider(
    budget: ExperimentConfig | None = None,
) -> LLMProvider:
    """Create the selected provider from environment variables."""
    provider = os.getenv("AGENTPROBE_PROVIDER", "mock").lower()
    model = os.getenv("AGENTPROBE_MODEL", "mock-deterministic")

    active_budget = budget or ExperimentConfig(
        max_tokens=int(os.getenv("AGENTPROBE_MAX_TOKENS", "100000")),
        max_spend_usd=float(os.getenv("AGENTPROBE_MAX_SPEND_USD", "1.0")),
    )

    input_rate = float(os.getenv("AGENTPROBE_INPUT_USD_PER_1K", "0"))

    output_rate = float(os.getenv("AGENTPROBE_OUTPUT_USD_PER_1K", "0"))

    if provider == "mock":
        return MockProvider(
            model=model,
            budget=active_budget,
            input_usd_per_1k=input_rate,
            output_usd_per_1k=output_rate,
        )

    if provider == "ollama":
        return OllamaProvider(
            model=model,
            budget=active_budget,
            input_usd_per_1k=input_rate,
            output_usd_per_1k=output_rate,
        )

    if provider == "hosted":
        return HostedProvider(
            model=model,
            budget=active_budget,
            input_usd_per_1k=input_rate,
            output_usd_per_1k=output_rate,
        )

    raise ValueError(f"Unknown AGENTPROBE_PROVIDER: {provider}")
