from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.semantic.state import *
from typing import List, Tuple, Dict
import tree_sitter


class CallGraphScanState(State):
    def __init__(self) -> None:
        """
        Maintain the caller-callee edges
        """
        self.caller_callee_edges: Dict[int, Tuple[tree_sitter.Node, set[int]]] = (
            {}
        )  # function_id -> (call_site, callee_ids)
        return

    def update_caller_callee_edges(
        self, caller_id: int, call_site_node: tree_sitter.Node, callee_ids: set[int]
    ) -> None:
        """
        Update the caller-callee edges
        """
        if caller_id not in self.caller_callee_edges:
            self.caller_callee_edges[caller_id] = (call_site_node, callee_ids)
        else:
            for single_call_site_node, single_callee_ids in self.caller_callee_edges[
                caller_id
            ][0]:
                if single_call_site_node == call_site_node:
                    single_callee_ids.update(callee_ids)
                    break
        return

    def get_callee_ids_of_call_site_at_caller(
        self, caller_id: int, call_site_node: tree_sitter.Node
    ) -> set[int]:
        """
        Get the callee ids of the call site at the caller
        """
        if caller_id not in self.caller_callee_edges:
            return set()
        for single_call_site_node, single_callee_ids in self.caller_callee_edges[
            caller_id
        ][0]:
            if single_call_site_node == call_site_node:
                return single_callee_ids
        return set()

    def get_caller_ids_of_callee(self, callee_id: int) -> set[int]:
        """
        Get the caller ids of the callee
        """
        caller_ids = set()
        for caller_id, (call_site_node, callee_ids) in self.caller_callee_edges.items():
            if callee_id in callee_ids:
                caller_ids.add(caller_id)
        return caller_ids
