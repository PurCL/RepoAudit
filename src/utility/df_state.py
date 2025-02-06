from utility.function import *
from utility.localvalue import *
from enum import Enum
from typing import List

class Status(Enum):
    Bug = 1
    Safe = 2
    Unknown = 3


class Path:
    def __init__(self, lines:str, state, status: str):
        self.lines = lines
        self.state = state
        self.children: List[(State, str, str, int)] = []
        self.dependency = ""
        self.sink:LocalValue = None
        self.set_status(status)

    def set_status(self, status: str):
        map = {
            "bug": Status.Bug,
            "safe": Status.Safe,
            "unknown": Status.Unknown
        }
        self.status = map[status.lower()]

    def get_status(self) -> str:
        return self.status.name
    
    def add_child(self, state, dependency: str, type: str, sink_line: int):
        """
        Add a child function to the path, type = "caller" or "callee"
        """
        self.children.append((state, dependency, type, sink_line))

    def __str__(self) -> str:
        return f"<Lines: {self.lines}, Source: `{self.state.source.name}`,  Function: `{self.state.function.function_name}`, Status: {self.get_status()}. File: {self.state.function.file_name}>"


class State:
    def __init__(self, source: LocalValue, function: Function):
        self.source = source
        self.function = function
        self.subpath : List[Path] = []
    
    def get_src_line(self) -> int:
        return self.source.line_number - self.function.start_line_number + 1
    
    def get_key(self) -> str:
        return f"<{self.source.name}, {self.function.function_name}>"
        