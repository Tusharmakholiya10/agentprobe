import uuid

import requests

from agentprobe.llm.wrapper import LLMProvider
from agentprobe.schemas import Task, Tool, ToolResult, Trace, TraceStep
from agentprobe.targets.base import BaseTarget


class WebResearchAgent(BaseTarget):
    def __init__(self, llm: LLMProvider, run_id: str | None = None):
        self.llm = llm
        self.run_id = run_id or str(uuid.uuid4())
        self.system_prompt = "You are a web researcher. Fetch pages and summarize them."

    def _fetch_page(self, url: str) -> str:
        try:
            # We strictly limit this to localhost for the sandbox rule
            if not url.startswith("http://localhost:") and not url.startswith(
                "http://127.0.0.1:"
            ):
                return "Error: Sandbox violation. Only localhost URLs permitted."

            resp = requests.get(url, timeout=2)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:  # <-- CHANGED THIS LINE
            return f"Error fetching page: {e!s}"

    def run(
        self, task_id: str, task_desc: str, tools: list[Tool] | None = None
    ) -> Trace:
        default_tools = [
            Tool(
                name="fetch_page",
                description="Fetch HTML of a URL",
                parameters={
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                },
            )
        ]
        active_tools = tools if tools is not None else default_tools

        trace = Trace(
            run_id=self.run_id,
            system_prompt=self.system_prompt,
            task=Task(id=task_id, description=task_desc),
        )

        context = f"Task: {task_desc}"
        for step_idx in range(3):
            resp, t_calls, stats = self.llm.generate(
                context, self.system_prompt, [t.model_dump() for t in active_tools]
            )

            trace.total_tokens += stats.get("prompt_tokens", 0) + stats.get(
                "completion_tokens", 0
            )
            trace.total_cost += stats.get("cost", 0.0)

            step = TraceStep(
                step_num=step_idx + 1,
                content=resp,
                latency_ms=stats.get("latency_ms", 0.0),
                tool_calls=t_calls,
            )

            if not t_calls:
                trace.final_answer = resp
                trace.steps.append(step)
                break

            for call in t_calls:
                res = "Error"
                if call.name == "fetch_page":
                    res = self._fetch_page(call.arguments.get("url", ""))
                step.tool_results.append(ToolResult(call_id=call.call_id, result=res))
                context += f"\nTool {call.name} returned: {res}"

            trace.steps.append(step)

        return trace
