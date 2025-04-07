from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.report.bug_report import *
from typing import List, Tuple, Dict


class SampleScanState:
    def __init__(self, seed_values: List[Tuple[Value, bool]]) -> None:
        """
        :param seed_values: the seed values indicating the potential buggy points or root causes
        """
        self.seed_values = seed_values
        self.sampled_seed_values = []
        self.bug_report_items: dict[Value, BugReport] = {}
        self.bug_report_lines: dict[int, Tuple[str, int]] = {}  # id --> file name, function id, line number
        self.total_bug_count = 0
        self.total_buggy_line_count = 0
        return
    

    def update_sampled_seed_values(self, sampled_seed_values: List[Tuple[Value, bool]]) -> None:
        """
        Update the sampled seed values
        :param seed_values: the sampled seed values
        """
        self.sampled_seed_values = sampled_seed_values
        return

    
    def update_bug_report(self, value: Value, bug_report: BugReport) -> None:
        """
        Update the bug scan state with the bug report
        :param bug_report: the bug report
        """
        self.bug_report_items[value] = bug_report
        loc = (value.file, value.line_number)
        if loc not in self.bug_report_lines.values():
            self.bug_report_lines[self.total_buggy_line_count] = (
                value.file,
                value.line_number
            )
        self.total_bug_count = len(self.bug_report_items)
        self.total_buggy_line_count = len(self.bug_report_lines)
        return
