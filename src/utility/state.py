from utility.function import *
from utility.localvalue import *
from typing import List

class State:
    def __init__(self, var: LocalValue, function: Function):
        self.var = var
        self.function = function
        self.slice = ""
        self.callers: List[State] = []
        self.callees: List[State] = []
    
    def get_src_line(self) -> int:
        return self.var.line_number - self.function.start_line_number + 1
    
    def get_key(self) -> str:
        return f"<{self.var.line_number}, {self.function.function_name}, {self.function.file_name}>"

    def find_root(self):
        """
        Find the root functions with no callers
        """
        root_list = []
        for caller in self.callers:
            root_list.extend(caller.find_root())
        if root_list == []:
            root_list.append(self)
        return root_list
    
    def get_slice_tree(self) -> List[str]:
        """
        Get the entire slice tree with the root as the current state
        """
        all_slices = [self.slice] if self.slice != "" else []
        for callee in self.callees:
            all_slices.extend(callee.get_slice_tree())
        return all_slices