"""Environment-driven provider construction."""

import os

from agentprobe.llm.base import LLMProvider
from agentprobe.llm.hosted import HostedProvider
from agentprobe.llm.mock import MockProvider
from agentprobe.llm.ollama import OllamaProvider
from agentprobe.schemas import ExperimentConfig


def create_provider(budget: ExperimentConfig | None = None) -> LLMProvider:
    """Create the selected provider from environment variables."""
    provider = os.getenv("AGENTPROBE_PROVIDER", "mock").lower()
    model = os.getenv("AGENTPROBE_MODEL", "mock-deterministic")
    kwargs: dict[str, object] = {
        "budget": budget or ExperimentConfig(
            max_tokens=int(os.getenv("AGENTPROBE_MAX_TOKENS", "100000")),
            max_spend_usd=float(os.getenv("AGENTPROBE_MAX_SPEND_USD", "1.0")),
        ),
        "input_usd_per_1k": float(os.getenv("AGENTPROBE_INPUT_USD_PER_1K", "0")),
        "output_usd_per_1k": float(os.getenv("AGENTPROBE_OUTPUT_USD_PER_1K", "0")),
    }
    if provider == "mock":
        return MockProvider(model=model, **kwargs)
    if provider == "ollama":
        return OllamaProvider(model=model, **kwargs)
    if provider == "hosted":
        return HostedProvider(model=model, **kwargs)
    raise ValueError(f"Unknown AGENTPROBE_PROVIDER: {provider}")
