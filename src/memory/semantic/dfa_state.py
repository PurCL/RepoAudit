from memory.syntactic.function import *
from memory.syntactic.value import *
from typing import List
from enum import Enum


class Status(Enum):
    Bug = 1
    Safe = 2
    Unknown = 3


class ExecutionPath:
    def __init__(self, lines: str, state, status: str):
        self.lines = lines
        self.state = state
        self.children: List[(DFAState, str)] = []  # (state, dependency)
        self.dependency = ""
        self.sink: Value = None
        self.set_status(status)

    def set_status(self, status: str):
        map = {"bug": Status.Bug, "safe": Status.Safe, "unknown": Status.Unknown}
        self.status = map[status.lower()]

    def get_status(self) -> str:
        return self.status.name

    def add_child(self, state, dependency: str, propagation_line: int):
        """
        Add a child state to the path (can be the caller or callee function of the current state)
        :param state: the child state
        :param dependency: the dependency of the src and child state
        :param propagation_line: the line number of the propagation
        """
        self.children.append((state, dependency, propagation_line))

    def __str__(self) -> str:
        return f"<Lines: {self.lines}, Source: `{self.state.var.name}`,  Function: `{self.state.function.function_name}`, Status: {self.get_status()}. File: {self.state.function.file_name}>"


class DFAState:
    def __init__(self, source: Value, function: Function):
        self.var = source
        self.function = function
        self.subpath: List[ExecutionPath] = []

    def get_src_line(self) -> int:
        return self.var.line_number - self.function.start_line_number + 1

    def get_key(self) -> str:
        return f"<{self.var.name}, {self.function.function_name}>"
