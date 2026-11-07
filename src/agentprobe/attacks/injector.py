from agentprobe.schemas import Attack
from agentprobe.targets.banking import BankingAgent
from agentprobe.targets.base import BaseTarget
from agentprobe.targets.email import EmailAgent
from agentprobe.targets.web import WebResearchAgent


class InjectionEngine:
    @staticmethod
    def inject(agent: BaseTarget, attack: Attack) -> None:
        """
        Places the attack payload into the appropriate location in the target's sandbox.
        """
        if isinstance(agent, EmailAgent) and attack.target == "email":
            # Inject into the first available email body
            if "msg_1" in agent.inbox:
                agent.inbox["msg_1"]["body"] += f"\n{attack.payload}"

        elif isinstance(agent, WebResearchAgent) and attack.target == "web":
            # For web, the injection engine will configure a specific test URL
            # but since the web agent fetches dynamically, we store it in a mock routing table
            # that the test fixture can read. (Handled via patching in tests or custom server)
            pass  # See test fixture for web injection logic

        elif isinstance(agent, BankingAgent) and attack.target == "banking":
            # Injecting as a fake system message into the task description or previous tool output
            # Handled at the run() wrapper level for banking.
            pass
