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
        self.refined_caller_callee_edges: Dict[int, Dict[int, List[int]]] = (
            {}
        )  # caller_id -> {call_site_node_id -> callee_ids}

        self.refined_callee_caller_edges: Dict[int, Dict[int, List[int]]] = (
            {}
        )  # callee_id -> {caller_id -> call_site_node_ids}
        return

    def update_caller_callee_edges(
        self, caller_id: int, call_site_node_id: int, callee_id: int
    ) -> None:
        """
        Update the caller-callee edges
        """
        if caller_id not in self.refined_caller_callee_edges:
            self.refined_caller_callee_edges[caller_id] = {
                call_site_node_id: [callee_id]
            }
        else:
            if call_site_node_id not in self.refined_caller_callee_edges[caller_id]:
                self.refined_caller_callee_edges[caller_id][call_site_node_id] = [
                    callee_id
                ]
            else:
                if (
                    callee_id
                    not in self.refined_caller_callee_edges[caller_id][
                        call_site_node_id
                    ]
                ):
                    self.refined_caller_callee_edges[caller_id][
                        call_site_node_id
                    ].append(callee_id)
        return

    def update_callee_caller_edge(
        self, callee_id: int, caller_id: int, call_site_node_id: int
    ) -> None:
        """
        Update the callee-caller edges
        """
        if callee_id not in self.refined_callee_caller_edges:
            self.refined_callee_caller_edges[callee_id] = {
                caller_id: [call_site_node_id]
            }
        else:
            if caller_id not in self.refined_callee_caller_edges[callee_id]:
                self.refined_callee_caller_edges[callee_id][caller_id] = [
                    call_site_node_id
                ]
            else:
                if (
                    call_site_node_id
                    not in self.refined_callee_caller_edges[callee_id][caller_id]
                ):
                    self.refined_callee_caller_edges[callee_id][caller_id].append(
                        call_site_node_id
                    )
        return
