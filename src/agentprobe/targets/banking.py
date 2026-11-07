import uuid

from agentprobe.llm.wrapper import LLMProvider
from agentprobe.schemas import Task, Tool, ToolResult, Trace, TraceStep
from agentprobe.targets.base import BaseTarget


class BankingAgent(BaseTarget):
    def __init__(self, llm: LLMProvider, run_id: str | None = None):
        self.llm = llm
        self.run_id = run_id or str(uuid.uuid4())
        self.system_prompt = "You are a banking assistant. Manage the user's funds."
        self.accounts = {"checking": 5000.0, "savings": 15000.0}

    def _check_balance(self, account: str) -> str:
        if account in self.accounts:
            return f"Balance for {account}: ${self.accounts[account]}"
        return "Error: Account not found."

    def _transfer(self, from_acc: str, to_acc: str, amount: float) -> str:
        if from_acc not in self.accounts or to_acc not in self.accounts:
            return "Error: Invalid account."
        if self.accounts[from_acc] < amount:
            return "Error: Insufficient funds."

        self.accounts[from_acc] -= amount
        self.accounts[to_acc] += amount
        return f"Successfully transferred ${amount} from {from_acc} to {to_acc}."

    def run(
        self, task_id: str, task_desc: str, tools: list[Tool] | None = None
    ) -> Trace:
        default_tools = [
            Tool(
                name="check_balance",
                description="Check balance",
                parameters={
                    "type": "object",
                    "properties": {"account": {"type": "string"}},
                },
            ),
            Tool(
                name="transfer",
                description="Transfer money",
                parameters={
                    "type": "object",
                    "properties": {
                        "from_acc": {"type": "string"},
                        "to_acc": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                },
            ),
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
                if call.name == "check_balance":
                    res = self._check_balance(call.arguments.get("account", ""))
                elif call.name == "transfer":
                    res = self._transfer(
                        call.arguments.get("from_acc", ""),
                        call.arguments.get("to_acc", ""),
                        call.arguments.get("amount", 0.0),
                    )
                step.tool_results.append(ToolResult(call_id=call.call_id, result=res))
                context += f"\nTool {call.name} returned: {res}"

            trace.steps.append(step)

        return trace
