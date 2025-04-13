from memory.semantic.state import State
from abc import ABC, abstractmethod
from typing import Dict
from typing import List, Optional


class Agent(ABC):
    def __init__(self) -> None:
        return

    @abstractmethod
    def start_scan(self) -> None:
        pass

    @abstractmethod
    def get_agent_state(self) -> State:
        pass
