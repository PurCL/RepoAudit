from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.report.bug_report import *
from typing import List, Tuple, Dict


class BugScanState:
    def __init__(self, seed_values: List[Tuple[Value, bool]]) -> None:
        """
        :param seed_values: the seed values indicating the potential buggy points or root causes
        """
        self.seed_values = seed_values
        self.bug_reports: dict[int, BugReport] = {}
        self.total_bug_count = 0
        return
    
    def update_state(self, bug_report: BugReport) -> None:
        """
        Update the bug scan state with the bug report
        :param bug_report: the bug report
        """
        self.bug_reports[self.total_bug_count] = bug_report
        self.total_bug_count += 1
        return
