from memory.syntactic.function import *
from memory.syntactic.api import *
from memory.syntactic.value import *
from memory.semantic.state import *
from llmtool.slicescan.intra_slicer import *
from tstool.analyzer.TS_analyzer import *
from typing import List, Dict, Tuple

class SliceScanState(State):
    def __init__(self, seed_function: Function, seed_values: List[Value], call_depth: int = 1, is_backward: bool = True):
        # Typically, there is only one seed. 
        # Here, we consider a set of seed values at the same program location with the same label
        # This is for efficiency improvement
        assert IntraSlicerInput.check_validity_of_seed_list(seed_values), "Invalid seed list"
        
        # Slicing setting
        self.seed_function = seed_function
        self.seed_values = sorted(set(seed_values), key=lambda seed: (seed.index, seed.name))
        self.call_depth = call_depth
        self.is_backward = is_backward

        # List of Tuple of SliceContext, function_id, seed values, and slice (as string)
        self.intra_slices : List[Tuple[CallContext, int, List[Value], str]] = []
        self.global_slices: List = []

        # Map from the function id to the function
        # The functions are the relevant ones in the slicing task
        self.relevant_functions : Dict[int, Function] = {}


    def update_intra_slices_in_state(self, call_context: CallContext, function: Function, values: List[Value], slice: str) -> None:
        """
        Update the state of the slicing task with the intra-procedural slice
        :param call_context: the context of the slice
        :param function: the function that the intra_slicer focues on
        :param value: the seed value that the intra_slicer focues on
        :param slice: the intra-procedural slice
        """
        self.intra_slices.append((call_context, function.function_id, values, slice))
        self.relevant_functions[function.function_id] = function
        return
    
    def update_global_slices_in_state(self, global_slice: str) -> None:
        """
        Update the state of the slicing task with the global slice
        :param global_slice: the global slice
        """
        self.global_slices.append(global_slice)
        return
    
    def get_result(self) -> str:
        """
        Get the final result of the slicing task
        The slice can be interprocedural
        """
        global_slice_str = "\n\n".join(self.global_slices)
        intra_slice_str = "\n\n".join([slice for (_, _, _, slice) in self.intra_slices])
        return f"{global_slice_str}\n\n{intra_slice_str}"
    
    def get_relevant_functions(self) -> List[Function]:
        """
        Get the relevant functions in the slicing task
        """
        return list(self.relevant_functions.values())
    
    def to_dict(self) -> dict:
        """
        Convert the state to a dictionary
        """
        return {
            "seed_function": {
                "file_path": self.seed_function.file_path,
                "function_name": self.seed_function.function_name,
                "function_code": self.seed_function.function_code
            },
            "seed_values": [str(seed_value) for seed_value in self.seed_values],
            "call_depth": self.call_depth,
            "is_backward": self.is_backward,
            "slice": self.get_result(),
        }
