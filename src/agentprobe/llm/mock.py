"""Deterministic, offline provider used by tests and CI."""

from time import perf_counter

from agentprobe.llm.base import LLMProvider, LLMResponse


class MockProvider(LLMProvider):
    """Return deterministic output without network access."""

    def __init__(self, model: str = "mock-deterministic", **kwargs: object) -> None:
        super().__init__(model=model, **kwargs)  # type: ignore[arg-type]

    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Return a stable response derived from the prompt."""
        self._check_budget()
        started = perf_counter()
        text = f"MOCK_RESPONSE: {prompt.strip()}"
        usage = self._usage(system_prompt + "\n" + prompt, text, started)
        return LLMResponse(text, usage, self.model, "mock")
