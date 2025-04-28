from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.report.bug_report import *
from memory.semantic.state import *
from typing import List, Tuple, Dict


class BugScanState(State):
    def __init__(self, seed_values: List[Tuple[Value, bool]]) -> None:
        """
        :param seed_values: the seed values indicating the potential buggy points or root causes
        """
        self.seed_values = seed_values
        self.seed_values_in_scope = []
        self.bug_reports: dict[int, BugReport] = {}
        self.total_bug_count = 0
        return

    def update_bug_report(self, bug_report: BugReport) -> None:
        """
        Update the bug scan state with the bug report
        :param bug_report: the bug report
        """
        self.bug_reports[self.total_bug_count] = bug_report
        self.total_bug_count += 1
        return

    def update_seed_values_in_scope(
        self, seed_values_in_scope: List[Tuple[Value, bool]]
    ) -> None:
        """
        Update the seed values in scope
        :param seed_values_in_scope: the seed values in scope
        """
        self.seed_values_in_scope = seed_values_in_scope
        return
