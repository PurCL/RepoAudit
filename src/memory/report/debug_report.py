from memory.syntactic.function import *
from memory.syntactic.value import *
from typing import Dict


class DebugReport:
    def __init__(
        self,
        error_message: str,
        slicing_seed: Value,
        slice: str,
        explanation: str,
        is_human_confirmed_true: bool = None,
    ) -> None:
        """
        :param error_message: the error message
        :param slicing_seed: the slicing seed
        :param slice: the retrieved slice
        :param explanation: the explanation
        """
        self.error_message = error_message
        self.slicing_seed = slicing_seed
        self.slice = slice
        self.explanation = explanation
        self.is_human_confirmed_true = is_human_confirmed_true
        return

    def to_dict(self) -> dict:
        return {
            "error_message": self.error_message,
            "slicing_seed": str(self.slicing_seed),
            "slice": self.slice,
            "explanation": self.explanation,
            "is_human_confirmed_true": (
                str(self.is_human_confirmed_true)
                if self.is_human_confirmed_true is not None
                else "unknown"
            ),
        }

    def __str__(self):
        return str(self.to_dict())
