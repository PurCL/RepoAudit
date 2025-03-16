from memory.syntactic.function import *
from memory.syntactic.api import *
from memory.syntactic.value import *
from llmtool.intra_slicer import *
from typing import List, Dict, Tuple

class ContextLabel(Enum):
    LEFT_PAR = -1
    RIGHT_PAR = 1

    def __str__(self) -> str:
        return self.name


class SliceContext:
    def __init__(self, is_backward: bool = True):
        self.context : List[Tuple[int, ContextLabel]] = []
        self.simplified_context : List[Tuple[int, ContextLabel]] = []
        self.is_backward = is_backward

    def add_context(self, function_id: int, label: ContextLabel) -> bool:
        """
        Add a context entry to the context
        :param function_id: the function id
        :param label: the label of the context entry
        :ret True if the context after adding the new context pair is in the CFL reachable, False otherwise
        """
        is_CFL_reachable = True
        if len(self.simplified_context) == 0:
            self.simplified_context.append((function_id, label))
            self.context.append((function_id, label))
            return is_CFL_reachable

        if not self.is_backward:
            (top_function_id, top_label) = self.simplified_context[-1]
            if top_label == label:
                self.simplified_context.append((function_id, label))
            elif top_label == ContextLabel.LEFT_PAR and label == ContextLabel.RIGHT_PAR:
                if top_function_id == function_id:
                    self.simplified_context.pop()
                else:
                    is_CFL_reachable = False
            else:
                # top_label == ContextLabel.RIGHT_PAR and label == ContextLabel.LEFT_PAR:
                self.simplified_context.append((function_id, label))

            if is_CFL_reachable:
                self.context.append((function_id, label))
        else:
            (top_function_id, top_label) = self.simplified_context[-1]
            if top_label == label:
                self.simplified_context.append((function_id, label))
            elif top_label == ContextLabel.RIGHT_PAR and label == ContextLabel.LEFT_PAR:
                if top_function_id == function_id:
                    self.simplified_context.pop()
                else:
                    is_CFL_reachable = False
            else:
                # top_label == ContextLabel.LEFT_PAR and label == ContextLabel.RIGHT_PAR:
                self.simplified_context.append((function_id, label))

            if is_CFL_reachable:
                self.context.append((function_id, label))
        return is_CFL_reachable


    def __str__(self) -> str:
        return f"SliceContext(is_backward={self.is_backward}, context={self.context})"
    
    def __eq__(self, other: 'SliceContext') -> bool:
        return str(self.context) == str(other.context) and self.is_backward == other.is_backward

    def __hash__(self) -> int:
        # Convert context list to tuple for hashing; assumes that context entries are immutable
        return hash((str(self.context), self.is_backward))
        

class SliceScanState:
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
        self.intra_slices : List[Tuple[SliceContext, int, List[Value], str]] = []
        self.global_slices: List = []

        # Map from the function id to the function
        # The functions are the relevant ones in the slicing task
        self.relevant_functions : Dict[int, Function] = {}


    def update_intra_slices_in_state(self, slice_context: SliceContext, function: Function, values: List[Value], slice: str) -> None:
        """
        Update the state of the slicing task with the intra-procedural slice
        :param slice_context: the context of the slice
        :param function: the function that the intra_slicer focues on
        :param value: the seed value that the intra_slicer focues on
        :param slice: the intra-procedural slice
        """
        self.intra_slices.append((slice_context, function.function_id, values, slice))
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
