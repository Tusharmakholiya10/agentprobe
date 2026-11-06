"""Deterministic scripted provider used by the offline baseline suite."""

from time import perf_counter

from agentprobe.llm.base import LLMProvider, LLMResponse


class ScriptedMockProvider(LLMProvider):
    """Replay pre-authored JSON model actions without network access."""

    def __init__(self, responses: list[str]) -> None:
        super().__init__(model="agentprobe-scripted-mock")
        self.responses = responses
        self.index = 0

    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Return the next scripted response and fail on unexpected extra calls."""
        self._check_budget(system_prompt + "\n" + prompt)
        if self.index >= len(self.responses):
            raise RuntimeError("Scripted mock ran out of responses")
        started = perf_counter()
        text = self.responses[self.index]
        self.index += 1
        usage = self._usage(system_prompt + "\n" + prompt, text, started)
        return LLMResponse(text, usage, self.model, "mock")
