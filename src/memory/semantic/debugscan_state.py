from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.report.debug_report import *
from memory.semantic.state import *
from typing import List, Tuple, Dict


class DebugScanState(State):
    def __init__(self, error_message: str) -> None:
        """
        :param seed_values: the seed values indicating the potential buggy points or root causes
        """
        self.error_message = error_message
        self.debug_seed: Value = None
        self.debug_report: DebugReport = None
        return

    def update_debug_seed(self, debug_seed: Value) -> None:
        """
        Update the debug seed
        :param debug_seed: the debug seed
        """
        self.debug_seed = debug_seed
        return

    def update_debug_report(self, debug_report: DebugReport) -> None:
        """
        Update the debug report
        :param debug_report: the debug report
        """
        self.debug_report = debug_report
        return
