import re
from enum import Enum

class ValueType(Enum):
    SRC = 1
    SINK = 2
    PARA = 3
    RET = 4
    ARG = 5
    OUT = 6
    BUF = 7
    GLOBAL = 8


class LocalValue:
    def __init__(
        self, name: str, line_number: int, v_type: ValueType, file: str="", index: int = -1
    ) -> None:
        self.name = name  # name can be a variable/parameter name or the expression tokenized string
        self.line_number = line_number
        self.index = index
        self.v_type = v_type
        self.file = file

    def __str__(self) -> str:
        return (
            "("
            + "("
            + self.name
            + ", "
            + str(self.index)
            + ", "
            + str(self.line_number)
            + ")"
            + ", "
            + str(self.v_type)
            + ", "
            + str(self.file)
            + ")"
        )

    def __repr__(self) -> str:
        return self.__str__()
    
    @staticmethod
    def from_string(s: str):
        pattern = r"\(\((.*), (-?\d+), (\d+)\), ValueType\.(\w+), (.*)\)"
        match = re.match(pattern, s)
        if match:
            name, index, line_number, v_type, file = match.groups()
            index = int(index)
            line_number = int(line_number)
            v_type = ValueType[v_type]
            return LocalValue(name, line_number, v_type, file, index)
        else:
            # raise ValueError("String does not match the expected format")
            print(f"String does not match the expected format: {s}")
