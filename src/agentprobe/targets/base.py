from abc import ABC, abstractmethod

from agentprobe.schemas import Tool, Trace


class BaseTarget(ABC):
    """
    Core interface that any agent must implement to be tested.
    """

    @abstractmethod
    def run(self, task_id: str, task_desc: str, tools: list[Tool]) -> Trace:
        pass
