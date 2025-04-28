import re
from typing import Set
from enum import Enum


class ValueLabel(Enum):
    SRC = 1
    SINK = 2
    PARA = 3
    RET = 4
    ARG = 5
    OUT = 6

    BUF_ACCESS_EXPR = 7  # buffer access
    NON_BUF_ACCESS_EXPR = 8  # non-buffer access

    LOCAL = 9
    GLOBAL = 10

    def __str__(self) -> str:
        mapping = {
            ValueLabel.SRC: "ValueLabel.SRC",
            ValueLabel.SINK: "ValueLabel.SINK",
            ValueLabel.PARA: "ValueLabel.PARA",
            ValueLabel.RET: "ValueLabel.RET",
            ValueLabel.ARG: "ValueLabel.ARG",
            ValueLabel.OUT: "ValueLabel.OUT",
            ValueLabel.BUF_ACCESS_EXPR: "ValueLabel.BUF_ACCESS_EXPR",
            ValueLabel.NON_BUF_ACCESS_EXPR: "ValueLabel.NON_BUF_ACCESS_EXPR",
            ValueLabel.LOCAL: "ValueLabel.LOCAL",
            ValueLabel.GLOBAL: "ValueLabel.GLOBAL",
        }
        return mapping[self]

    @staticmethod
    def from_str(s: str):
        mapping = {
            "ValueLabel.SRC": ValueLabel.SRC,
            "ValueLabel.SINK": ValueLabel.SINK,
            "ValueLabel.PARA": ValueLabel.PARA,
            "ValueLabel.RET": ValueLabel.RET,
            "ValueLabel.ARG": ValueLabel.ARG,
            "ValueLabel.OUT": ValueLabel.OUT,
            "ValueLabel.BUF_ACCESS_EXPR": ValueLabel.BUF_ACCESS_EXPR,
            "ValueLabel.NON_BUF_ACCESS_EXPR": ValueLabel.NON_BUF_ACCESS_EXPR,
            "ValueLabel.LOCAL": ValueLabel.LOCAL,
            "ValueLabel.GLOBAL": ValueLabel.GLOBAL,
        }
        try:
            return mapping[s]
        except KeyError:
            raise ValueError(f"Invalid label: {s}")


class Value:
    def __init__(
        self, name: str, line_number: int, label: ValueLabel, file: str, index: int = -1
    ) -> None:
        """
        :param name: the name of the value. It can be a variable/parameter name or the expression tokenized string
        :param line_number: the line number of the value
        :param label: the label of the value
        :param file: the file path of the value
        :param index: the index of the value. For PARA, RET, ARG, it start from 0. Otherwise, it is -1.
        """
        self.name = name
        self.line_number = line_number
        self.label = label
        self.file = file
        self.index = index

    def __str__(self) -> str:
        return (
            "("
            + "("
            + self.name
            + ", "
            + str(self.file)
            + ", "
            + str(self.line_number)
            + ", "
            + str(self.index)
            + ")"
            + ", "
            + str(self.label)
            + ")"
        )

    def __eq__(self, other: "Value") -> bool:
        return self.__str__() == other.__str__()

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self) -> int:
        return hash(self.__str__())

    @classmethod
    def from_str_to_value(cls, s: str) -> "Value":
        """
        Parse a string of the format:
            "((name, file, line_number, index), label)"
        and create a Value instance from it.
        """
        pattern = r"^\(\(\s*(?P<name>[^,]+),\s*(?P<file>[^,]+),\s*(?P<line_number>\d+),\s*(?P<index>-?\d+)\s*\),\s*(?P<label>[^)]+)\)$"
        match = re.match(pattern, s)
        if not match:
            raise ValueError(f"String does not match expected format: {s}")

        name = match.group("name").strip()
        file = match.group("file").strip()
        line_number = int(match.group("line_number"))
        index = int(match.group("index"))
        label_str = match.group("label").strip()

        return cls(name, line_number, ValueLabel.from_str(label_str), file, index)
