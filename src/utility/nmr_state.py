from utility.function import *
from utility.localvalue import *
from typing import List

class State:
    def __init__(self, var: LocalValue, function: Function, abs:str = ""):
        self.var = var
        self.abs = abs
        self.function = function
        self.expressions: List[str] = []
        self.children: List[State] = []
    
    def get_src_line(self) -> int:
        return self.var.line_number - self.function.start_line_number + 1
    
    def get_key(self) -> str:
        return f"<{self.var.name}, {self.function.function_name}>"
    
    def get_all_expressions(self) -> List[str]:
        expressions = []
        for child in self.children:
            expressions.extend(child.get_all_expressions())
        expressions.append(self.expressions)
        return expressions
    
    def print_all_expressions(self) -> None:
        for child in self.children:
            child.print_all_expressions()
        print(f"\nFunction: {self.function.function_name}")
        for expression in self.expressions:
            print(expression)

        