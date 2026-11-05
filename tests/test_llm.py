"""Provider and budget tests; all tests are offline."""

import pytest

from agentprobe.llm import create_provider
from agentprobe.llm.base import BudgetExceeded
from agentprobe.llm.mock import MockProvider
from agentprobe.schemas import ExperimentConfig


def test_mock_is_deterministic() -> None:
    """Mock output is stable for identical prompts."""
    provider = MockProvider()
    assert provider.generate("hello").text == provider.generate("hello").text


def test_mock_tracks_usage() -> None:
    """Mock responses report token estimates and latency."""
    response = MockProvider().generate("hello", "system")
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
    assert response.usage.latency_ms >= 0


def test_token_budget_stops_next_call() -> None:
    """A consumed token budget prevents the next provider call."""
    provider = MockProvider(budget=ExperimentConfig(max_tokens=1, max_spend_usd=1))
    with pytest.raises(BudgetExceeded):
        provider.generate("this prompt exceeds the tiny budget")


def test_factory_defaults_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default provider is the offline mock."""
    monkeypatch.delenv("AGENTPROBE_PROVIDER", raising=False)
    assert create_provider().generate("ok").provider == "mock"
