from memory.syntactic.function import *
from memory.syntactic.value import *
from typing import Dict


class BugReport:
    def __init__(
        self,
        bug_type: str,
        buggy_value: Value,
        relevant_functions: Dict[int, Function],
        explanation: str,
        is_human_confirmed_true: bool = None,
    ) -> None:
        """
        :param bug_type: the bug type
        :param buggy_value: the buggy value
        :param relevant_functions: the relevant functions
        :param explanation: the explanation
        """
        self.bug_type = bug_type
        self.buggy_value = buggy_value
        self.relevant_functions = relevant_functions
        self.explanation = explanation
        self.is_human_confirmed_true = is_human_confirmed_true
        return

    def to_dict(self) -> dict:
        return {
            "bug_type": self.bug_type,
            "buggy_value": str(self.buggy_value),
            "relevant_functions": [
                [
                    self.relevant_functions[function_id].file_path
                    for function_id in self.relevant_functions
                ],
                [
                    self.relevant_functions[function_id].function_name
                    for function_id in self.relevant_functions
                ],
                [
                    self.relevant_functions[function_id].function_code
                    for function_id in self.relevant_functions
                ],
            ],
            "explanation": self.explanation,
            "is_human_confirmed_true": (
                str(self.is_human_confirmed_true)
                if self.is_human_confirmed_true is not None
                else "unknown"
            ),
        }

    def __str__(self):
        return str(self.to_dict())
