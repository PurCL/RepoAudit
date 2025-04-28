from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.report.bug_report import *
from memory.semantic.state import *
from typing import List, Tuple, Dict


class MetaScanState(State):
    def __init__(self) -> None:
        self.function_meta_data_dict = {}  # function id --> function meta data
        return

    def update_function_meta_data(
        self, function_id: int, function_meta_data: Dict
    ) -> None:
        """
        Update the sampled seed values
        :param seed_values: the sampled seed values
        """
        self.function_meta_data_dict[function_id] = function_meta_data
        return
