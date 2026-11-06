"""Target protocol, function adapter, and shared tool-calling runtime."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from agentprobe.llm.base import LLMProvider
from agentprobe.schemas import Tool, ToolCall, ToolResult, Trace, TraceEventType
from agentprobe.tracer import SQLiteTracer


class Target(Protocol):
    """A runnable agent target whose executions are persisted as traces."""

    def run(self, task: str, tools: list[Tool]) -> Trace:
        """Execute one task and return its complete trace."""


class StepLimitExceeded(RuntimeError):
    """Raised when an agent attempts more tool calls than allowed."""


@dataclass(frozen=True)
class ToolBinding:
    """A public tool schema paired with its sandbox-only implementation."""

    schema: Tool
    handler: Callable[[dict[str, Any]], Any]


def wrap_function(
    name: str,
    description: str,
    handler: Callable[[dict[str, Any]], Any],
    parameters: dict[str, Any] | None = None,
) -> ToolBinding:
    """Expose a Python function as a declared tool with a sandbox handler."""
    return ToolBinding(
        Tool(name=name, description=description, parameters=parameters or {}),
        handler,
    )


class FunctionTarget:
    """Adapt a simple existing Python agent function to the Target protocol."""

    def __init__(
        self, function: Callable[[str], str], tracer: SQLiteTracer, system_prompt: str
    ) -> None:
        self.function = function
        self.tracer = tracer
        self.system_prompt = system_prompt

    def run(self, task: str, tools: list[Tool]) -> Trace:
        """Run the wrapped function and persist its input and output."""
        del tools
        run_id = self.tracer.start_run(self.system_prompt, task)
        try:
            answer = self.function(task)
            self.tracer.finish_run(run_id, answer)
        except Exception as exc:
            self.tracer.add_event(
                run_id, TraceEventType.RUN_ABORTED, {"reason": str(exc)}
            )
            self.tracer.abort_run(run_id, str(exc))
            raise
        return self.tracer.get_trace(run_id)


def wrap_agent(
    function: Callable[[str], str],
    tracer: SQLiteTracer,
    system_prompt: str = "Wrapped agent",
) -> Target:
    """Wrap a plain agent function without requiring an agent framework."""
    return FunctionTarget(function, tracer, system_prompt)


class ToolCallingAgent:
    """Plain LLM tool loop with bounded steps and complete trace instrumentation."""

    def __init__(
        self,
        provider: LLMProvider,
        tracer: SQLiteTracer,
        system_prompt: str,
        bindings: list[ToolBinding],
        max_steps: int = 8,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.provider = provider
        self.tracer = tracer
        self.system_prompt = system_prompt
        self.bindings = {binding.schema.name: binding for binding in bindings}
        if len(self.bindings) != len(bindings):
            raise ValueError("Tool names must be unique")
        self.tools = [binding.schema for binding in bindings]
        self.max_steps = max_steps

    def run(self, task: str, tools: list[Tool] | None = None) -> Trace:
        """Run a JSON-directed tool loop; every model and tool event is recorded."""
        exposed = tools if tools is not None else self.tools
        allowed = {tool.name for tool in exposed}
        if not allowed.issubset(self.bindings):
            raise ValueError("Requested tool list contains an unbound tool")
        run_id = self.tracer.start_run(self.system_prompt, task)
        transcript: list[dict[str, Any]] = [{"role": "user", "content": task}]
        steps = 0
        try:
            while True:
                prompt = (
                    "Return exactly one JSON object: either "
                    '{"tool_call":{"name":"tool_name","arguments":{...}}} or '
                    '{"final":"answer"}.\n'
                    f"Available tools: {json.dumps([t.model_dump() for t in exposed])}\n"
                    f"Conversation: {json.dumps(transcript, default=str)}"
                )
                response = self.provider.generate(prompt, self.system_prompt)
                self.tracer.add_event(
                    run_id,
                    TraceEventType.LLM_CALL,
                    {
                        "provider": response.provider,
                        "model": response.model,
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": prompt[:20000]},
                        ],
                        "response": response.text[:20000],
                    },
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    latency_ms=response.usage.latency_ms,
                    estimated_cost_usd=response.usage.estimated_cost_usd,
                )
                message = json.loads(response.text)
                if isinstance(message, dict) and isinstance(message.get("final"), str):
                    answer = message["final"]
                    self.tracer.finish_run(run_id, answer)
                    return self.tracer.get_trace(run_id)
                call_data = message.get("tool_call") if isinstance(message, dict) else None
                if not isinstance(call_data, dict):
                    raise ValueError("Model response must contain a tool_call or final field")
                name = call_data.get("name")
                arguments = call_data.get("arguments", {})
                if not isinstance(name, str) or not isinstance(arguments, dict):
                    raise ValueError("Tool call requires a string name and object arguments")
                if name not in allowed:
                    raise ValueError(f"Tool is not available to this target: {name}")
                if steps >= self.max_steps:
                    raise StepLimitExceeded(
                        f"Agent exceeded the {self.max_steps}-step tool limit"
                    )
                call = ToolCall(name=name, arguments=arguments)
                self.tracer.add_event(
                    run_id,
                    TraceEventType.TOOL_CALL,
                    {"id": call.id, "name": call.name, "arguments": call.arguments},
                )
                steps += 1
                try:
                    output = self.bindings[name].handler(arguments)
                    result = ToolResult(tool_call_id=call.id, output=output)
                    transcript.append({"role": "tool", "name": name, "output": output})
                except Exception as exc:
                    result = ToolResult(tool_call_id=call.id, error=str(exc))
                    transcript.append({"role": "tool", "name": name, "error": str(exc)})
                self.tracer.add_event(
                    run_id,
                    TraceEventType.TOOL_RESULT,
                    {
                        "tool_call_id": result.tool_call_id,
                        "name": name,
                        "output": result.output,
                        "error": result.error,
                    },
                )
        except Exception as exc:
            self.tracer.add_event(
                run_id, TraceEventType.RUN_ABORTED, {"reason": str(exc)}
            )
            self.tracer.abort_run(run_id, str(exc))
            raise
