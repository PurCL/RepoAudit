from memory.syntactic.function import *
from memory.syntactic.value import *
from typing import List, Tuple, Dict
from memory.report.bug_report import *
from tstool.analyzer.TS_analyzer import *
    

class DFBState:
    def __init__(self, src_values: List[Value], sink_values: List[Value]) -> None:
        self.src_values = src_values
        self.sink_values = sink_values

        self.reachable_values_per_path: Dict[Tuple[Value, CallContext], List[Set[Tuple[Value, CallContext]]]] = {}
        self.external_value_match: Dict[Tuple[Value, CallContext], Set[Tuple[Value, CallContext]]] = {}
        
        self.potential_buggy_paths: Dict[str, List[Value]] = {}
        self.bug_reports: dict[Value, List[BugReport]] = {}
        self.total_bug_count = 0
        return
    

    def update_reachable_values_per_path(self, start: Tuple[Value, CallContext], ends: Set[Tuple[Value, CallContext]]) -> None:
        """
        Update the reachable values per path
        """
        if start not in self.reachable_values_per_path:
            self.reachable_values_per_path[start] = []
        self.reachable_values_per_path[start].append(ends)
        return
    
    
    def update_external_value_match(self, external_start: Tuple[Value, CallContext], external_ends: Set[Tuple[Value, CallContext]]) -> None:
        """
        Update the external value match
        """
        if external_start not in self.external_value_match:
            self.external_value_match[external_start] = set()
        self.external_value_match[external_start].update(external_ends)
        return
    
    def update_potential_buggy_paths(self, path: List[Value]) -> None:
        """
        Update the buggy paths
        """
        path_str = str(path)
        self.potential_buggy_paths[path_str] = path
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
    
    def print_reachable_values_per_path(self) -> None:
        """
        Print the reachable values per path
        """
        print("=====================================")
        print("Reachable Values Per Path:")
        print("=====================================")
        for (start_value, start_context), ends in self.reachable_values_per_path.items():
            print("-------------------------------------")
            print(f"Start: {str(start_value)}, {str(start_context)}")
            for i in range(len(ends)):
                print("--------------------------")
                print(f"  Path {i + 1}:")
                for (value, ctx) in ends[i]:
                    print(f"  End: {value}, {str(ctx)}")
                print("--------------------------")
            print("-------------------------------------")
        print("=====================================\n")
        return
    
    def print_external_value_match(self) -> None:
        """
        Print the external value match.
        """
        print("=====================================")
        print("External Value Match:")
        print("=====================================")
        for start, ends in self.external_value_match.items():
            print("-------------------------------------")
            print(f"Start: {start[0]}, {str(start[1])}")
            for end in ends:
                # end is a tuple of (Value, CallContext)
                print(f"  End: {end[0]}, {str(end[1])}")
            print("-------------------------------------")
        print("=====================================\n")
        return

    def print_potential_buggy_paths(self) -> None:
        """
        Print the potential buggy paths
        """
        print("=====================================")
        print("Potential Buggy Paths:")
        print("=====================================")
        path_id = 0
        for path_str, path in self.potential_buggy_paths.items():
            print("-------------------------------------")
            print(f"Path ID: {path_id}")
            path_id += 1
            for value in path:
                print(f"  Value: {value}")
            print("-------------------------------------")
        print("=====================================\n")
        return
