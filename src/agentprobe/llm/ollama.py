"""Ollama local HTTP provider, implemented with the standard library."""

import json
import os
from time import perf_counter
from urllib.error import URLError
from urllib.request import Request, urlopen

from agentprobe.llm.base import LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """Call a locally hosted Ollama chat completion endpoint."""

    def __init__(self, model: str, base_url: str | None = None, **kwargs: object) -> None:
        super().__init__(model=model, **kwargs)  # type: ignore[arg-type]
        self.base_url = (base_url or os.getenv("AGENTPROBE_OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")

    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Generate a response using Ollama's /api/chat endpoint."""
        self._check_budget()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({"model": self.model, "messages": messages, "stream": False}).encode()
        request = Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = perf_counter()
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode())
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        text = str(payload.get("message", {}).get("content", ""))
        usage = self._usage(system_prompt + "\n" + prompt, text, started)
        if "prompt_eval_count" in payload:
            usage = type(usage)(
                int(payload["prompt_eval_count"]),
                int(payload.get("eval_count", usage.output_tokens)),
                usage.latency_ms,
                usage.estimated_cost_usd,
            )
            self.total_tokens += usage.input_tokens + usage.output_tokens - (
                self.count_tokens(system_prompt + "\n" + prompt) + self.count_tokens(text)
            )
        return LLMResponse(text, usage, self.model, "ollama")
