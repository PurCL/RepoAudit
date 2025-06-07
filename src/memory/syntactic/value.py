import re
from typing import Optional, Set
from enum import Enum

from errors import RAValueError

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory.syntactic.function import Function


class ValueLabel(Enum):
    SRC = 1
    SINK = 2

    # A function parameter could be an ordinary parameter, a variadic parameter, or an explicit object parameter.
    # Some programming languages (e.g., C++ and Go) allow a function to have a variadic parameter, which is a parameter that can accept a variable number of arguments.
    # Some programming languages (e.g.,  Go and Python) use explicit object parameters, while others (e.g., C++ and Java) use implicit object parameters (e.g., `this`).
    PARA = 3000  # oridinary parameter
    VARI_PARA = 3001  # variadic parameter
    OBJ_PARA = 3002  # explicit object parameter

    ARG = 4000  # ordinary argument
    OBJ_ARG = 4001  # receiver object argument

    RET = 5
    OUT = 6

    BUF_ACCESS_EXPR = 7  # buffer access
    NON_BUF_ACCESS_EXPR = 8  # non-buffer access

    LOCAL = 9
    GLOBAL = 10

    CONSTANT = 11  # literal value, e.g., a string or a number
    DECLARATION = 12  # declaration of a variable or a function

    def __str__(self) -> str:
        mapping = {
            ValueLabel.SRC: "ValueLabel.SRC",
            ValueLabel.SINK: "ValueLabel.SINK",
            ValueLabel.PARA: "ValueLabel.PARA",
            ValueLabel.VARI_PARA: "ValueLabel.VARI_PARA",
            ValueLabel.OBJ_PARA: "ValueLabel.OBJ_PARA",
            ValueLabel.ARG: "ValueLabel.ARG",
            ValueLabel.OBJ_ARG: "ValueLabel.OBJ_ARG",
            ValueLabel.RET: "ValueLabel.RET",
            ValueLabel.OUT: "ValueLabel.OUT",
            ValueLabel.BUF_ACCESS_EXPR: "ValueLabel.BUF_ACCESS_EXPR",
            ValueLabel.NON_BUF_ACCESS_EXPR: "ValueLabel.NON_BUF_ACCESS_EXPR",
            ValueLabel.LOCAL: "ValueLabel.LOCAL",
            ValueLabel.GLOBAL: "ValueLabel.GLOBAL",
            ValueLabel.CONSTANT: "ValueLabel.CONSTANT",
            ValueLabel.DECLARATION: "ValueLabel.DECLARATION",
        }
        return mapping[self]

    def is_para(self) -> bool:
        """
        :return: True if the label is a parameter
        """
        return self in {ValueLabel.PARA, ValueLabel.VARI_PARA, ValueLabel.OBJ_PARA}

    def is_arg(self) -> bool:
        """
        :return: True if the label is an argument
        """
        return self in {ValueLabel.ARG, ValueLabel.OBJ_ARG}

    @staticmethod
    def from_str(s: str):
        mapping = {
            "ValueLabel.SRC": ValueLabel.SRC,
            "ValueLabel.SINK": ValueLabel.SINK,
            "ValueLabel.PARA": ValueLabel.PARA,
            "ValueLabel.VARI_PARA": ValueLabel.VARI_PARA,
            "ValueLabel.OBJ_PARA": ValueLabel.OBJ_PARA,
            "ValueLabel.ARG": ValueLabel.ARG,
            "ValueLabel.OBJ_ARG": ValueLabel.OBJ_ARG,
            "ValueLabel.RET": ValueLabel.RET,
            "ValueLabel.OUT": ValueLabel.OUT,
            "ValueLabel.BUF_ACCESS_EXPR": ValueLabel.BUF_ACCESS_EXPR,
            "ValueLabel.NON_BUF_ACCESS_EXPR": ValueLabel.NON_BUF_ACCESS_EXPR,
            "ValueLabel.LOCAL": ValueLabel.LOCAL,
            "ValueLabel.GLOBAL": ValueLabel.GLOBAL,
            "ValueLabel.CONSTANT": ValueLabel.CONSTANT,
            "ValueLabel.DECLARATION": ValueLabel.DECLARATION,
        }
        try:
            return mapping[s]
        except KeyError:
            raise RAValueError(f"Invalid label: {s}")


class Value:
    def __init__(
        self,
        name: str,
        line_number: int,
        label: ValueLabel,
        file: str,
        index: int = -1,
        comment: Optional[str] = None,
    ) -> None:
        """
        :param name: the name of the value. It can be a variable/parameter name or the expression tokenized string
        :param line_number: the line number of the value
        :param label: the label of the value
        :param file: the file path of the value
        :param index: the index of the value. For PARA, RET, ARG, it start from 0. Otherwise, it is -1.
        :param comment: the comment of the value, if any
        """
        self.name = name
        self.line_number = line_number
        self.label = label
        self.file = file
        self.index = index
        self.comment = (
            comment  # optional, `comment` is not used in __str__ and __eq__ methods
        )

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Value):
            return NotImplemented

        return self.__str__() == other.__str__()

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self) -> int:
        return hash(self.__str__())

    def description(self, func: "Function") -> str:
        """
        :return: the description of the value
        """
        # XXX (ZZ): We try to make the description human-readable, such as
        #    - the first argument `a1` (i.e., `a1` at index 0) at line 1 of this function
        #    - the src field of the receiver argument `a1` at line 1 of this function
        # Type description
        mapping = {
            ValueLabel.SRC: "source",
            ValueLabel.SINK: "sink",
            ValueLabel.PARA: "parameter",
            ValueLabel.VARI_PARA: "element of the variadic parameter",
            ValueLabel.OBJ_PARA: "object parameter",
            ValueLabel.ARG: "argument",
            ValueLabel.OBJ_ARG: "receiver object argument",
            ValueLabel.RET: "return value at",
            ValueLabel.OUT: "output value of",
            ValueLabel.BUF_ACCESS_EXPR: "buffer access expression",
            ValueLabel.NON_BUF_ACCESS_EXPR: "non-buffer access expression",
            ValueLabel.LOCAL: "local variable",
            ValueLabel.GLOBAL: "global variable",
            ValueLabel.CONSTANT: "constant value",
            ValueLabel.DECLARATION: "declared variable",
        }
        type_description = mapping.get(self.label)
        if type_description is None:
            raise RAValueError(f"Invalid label: {self.label}")

        # Index description
        if self.index != -1:
            if self.index % 10 == 0:
                index_description = f"the {self.index + 1}st"
            elif self.index % 10 == 1:
                index_description = f"the {self.index + 1}nd"
            elif self.index % 10 == 2:
                index_description = f"the {self.index + 1}rd"
            else:
                index_description = f"the {self.index + 1}th"

            description = f"{index_description} {type_description} `{self.name}` (at index {self.index})"
        else:
            description = f"the {type_description} `{self.name}`"

        # File and line number description
        if self.line_number > 0:
            line_number = self.line_number - func.start_line_number + 1
            description += (
                f" at line {line_number} of this function `{func.function_name}`"
            )
        else:
            description += f" of this function `{func.function_name}`"

        # Additional/Optional comment
        if self.comment is not None:
            return self.comment.format(description=description)
        else:
            return description

    ### TODO (ZZ): TO REMOVE
    def type_description(self) -> str:
        """
        :return: the type description of the value
        """
        mapping = {
            ValueLabel.SRC: "source",
            ValueLabel.SINK: "sink",
            ValueLabel.PARA: "parameter",
            ValueLabel.VARI_PARA: "element of the variadic parameter",
            ValueLabel.OBJ_PARA: "object parameter",
            ValueLabel.ARG: "argument",
            ValueLabel.OBJ_ARG: "receiver object argument",
            ValueLabel.RET: "return value at",
            ValueLabel.OUT: "output value of",
            ValueLabel.BUF_ACCESS_EXPR: "buffer access expression",
            ValueLabel.NON_BUF_ACCESS_EXPR: "non-buffer access expression",
            ValueLabel.LOCAL: "local variable",
            ValueLabel.GLOBAL: "global variable",
            ValueLabel.CONSTANT: "literal value",
            ValueLabel.DECLARATION: "declared variable",
        }
        type_description = mapping.get(self.label)
        if type_description is None:
            raise RAValueError(f"Invalid label: {self.label}")

        if self.index != -1:
            if self.index % 10 == 0:
                type_description = f"the {self.index + 1}st (i.e., index {self.index}) {type_description}"
            elif self.index % 10 == 1:
                type_description = f"the {self.index + 1}nd (i.e., index {self.index}) {type_description}"
            elif self.index % 10 == 2:
                type_description = f"the {self.index + 1}rd (i.e., index {self.index}) {type_description}"
            else:
                type_description = f"the {self.index + 1}th (i.e., index {self.index}) {type_description}"

        return type_description

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
            raise RAValueError(f"String does not match expected format: {s}")

        name = match.group("name").strip()
        file = match.group("file").strip()
        line_number = int(match.group("line_number"))
        index = int(match.group("index"))
        label_str = match.group("label").strip()

        return cls(name, line_number, ValueLabel.from_str(label_str), file, index)
