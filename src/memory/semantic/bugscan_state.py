from memory.syntactic.function import *
from memory.syntactic.value import *
from typing import List, Tuple, Dict


class BugReport:
    def __init__(self, 
                 bug_type: str, 
                 buggy_value: Value, 
                 buggy_function: Function,
                 relevant_functions: Dict[int, Function], 
                 tree_str: str,
                 slice: str,
                 inlined_slice: str,
                 poc_str: str) -> None:
        """
        :param bug_type: the type of bug
        :param buggy_value: the buggy value
        :param buggy_function: the buggy function
        :param relevant_functions: the relevant functions
        :param call_tree: the call tree, showing the caller-callee relationship in tree format
        :param slice: the slice consisting of the intra-slice and global-slice
        :param inlined_slice: the inlined slice that simplify the buggy semantics of the bug report
        :param poc_str: the proof of concept string as bug explanation
        """
        self.bug_type = bug_type
        self.buggy_value = buggy_value
        self.buggy_function = buggy_function
        self.relevant_functions = relevant_functions
        self.call_tree = tree_str
        self.slice = slice
        self.inlined_slice = inlined_slice
        self.poc_str = poc_str
        return
    
    def to_dict(self) -> dict:
        return {
            "bug_type": self.bug_type,
            "buggy_value": str(self.buggy_value),
            "buggy_function": self.buggy_function.function_name,
            "relevant_functions": [self.relevant_functions[function_id].lined_code for function_id in self.relevant_functions],
            "call_tree": self.call_tree,
            "slice": self.slice,
            "inlined_slice": self.inlined_slice,
            "poc_str": self.poc_str,
        }
    
    def __str__(self):
        return str(self.to_dict())
    

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
