from utility.function import *
from utility.localvalue import *
from typing import List

class State:
    def __init__(self, var: LocalValue, function: Function):
        self.var = var
        self.function = function
        self.slice = ""
        self.children: List[State] = []
    
    def get_src_line(self) -> int:
        return self.var.line_number - self.function.start_line_number + 1
    
    def get_key(self) -> str:
        return f"<{self.var.line_number}, {self.function.function_name}, {self.function.file_name}>"
    
    def get_all_slices(self) -> List[str]:
        """
        Get all children slices
        """
        all_slices = [self.slice] if self.slice != "" else []
        for child in self.children:
            all_slices.extend(child.get_all_slices())
        return all_slices

        