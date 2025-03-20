from memory.syntactic.function import *
from memory.syntactic.value import *
from typing import List, Tuple, Dict
from memory.report.bug_report import *
    

class DFBState:
    def __init__(self, src_values: List[Value], sink_values: List[Value]) -> None:
        self.src_values = src_values
        self.sink_values = sink_values

        self.reachable_values_per_path: Dict[Value, List[Set[Value]]] = {}
        self.bug_reports: dict[Value, List[BugReport]] = {}
        self.total_bug_count = 0
        return
    

    def update_reachable_values_per_path(self, value: Value, path: List[Value]) -> None:
        """
        Update the reachable values per path
        :param value: the value
        :param path: the path
        """
        if value not in self.reachable_values_per_path:
            self.reachable_values_per_path[value] = []
        self.reachable_values_per_path[value].append(set(path))
        return

    def update_bug_reports(self, value: Value, bug_report: BugReport) -> None:
        """
        Update the bug reports
        :param value: the value
        :param bug_report: the bug report
        """
        if value not in self.bug_reports:
            self.bug_reports[value] = []
        self.bug_reports[value].append(bug_report)
        self.total_bug_count += 1
        return
