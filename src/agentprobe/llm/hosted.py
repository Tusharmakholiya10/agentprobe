"""OpenAI-compatible hosted chat-completions provider using urllib."""

import json
import os
from time import perf_counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agentprobe.llm.base import LLMProvider, LLMResponse, Usage


class HostedProvider(LLMProvider):
    """Call an explicitly configured OpenAI-compatible endpoint."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(model=model, **kwargs)  # type: ignore[arg-type]
        self.base_url = (base_url or os.getenv("AGENTPROBE_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("AGENTPROBE_API_KEY", "")
        if not self.api_key:
            raise ValueError("AGENTPROBE_API_KEY is required when provider=hosted.")

    def generate(self, prompt: str, system_prompt: str = "") -> LLMResponse:
        """Generate a chat completion and normalize provider usage."""
        self._check_budget()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        body = json.dumps({"model": self.model, "messages": messages, "stream": False}).encode()
        request = Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        started = perf_counter()
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode())
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"Hosted provider returned HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Hosted provider request failed: {exc}") from exc
        text = str(payload["choices"][0]["message"]["content"])
        elapsed = (perf_counter() - started) * 1000
        reported = payload.get("usage", {})
        input_tokens = int(reported.get("prompt_tokens", self.count_tokens(system_prompt + prompt)))
        output_tokens = int(reported.get("completion_tokens", self.count_tokens(text)))
        cost = (
            input_tokens * self.input_usd_per_1k + output_tokens * self.output_usd_per_1k
        ) / 1000
        usage = Usage(input_tokens, output_tokens, elapsed, cost)
        self.total_tokens += input_tokens + output_tokens
        self.total_cost_usd += cost
        if self.total_tokens > self.budget.max_tokens or self.total_cost_usd > self.budget.max_spend_usd:
            raise RuntimeError("Call completed but exceeded the configured budget; run aborted.")
        return LLMResponse(text, usage, self.model, "hosted")
