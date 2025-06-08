import copy
from typing import Dict, List, Optional, Set, Tuple
from tree_sitter import Node

from utility.errors import RAAnalysisError
from memory.syntactic.value import Value, ValueLabel

Scope = Tuple[int, int]
IfStatement = Tuple[int, int, str, Scope, Scope]
LoopStatement = Tuple[int, int, str, int, int]


class Function:
    def __init__(
        self,
        function_id: int,
        function_name: str,
        function_code: str,
        start_line_number: int,
        end_line_number: int,
        function_node: Node,
        file_path: str,
    ) -> None:
        """
        Record basic facts of the function.
        Here, the function indicates a user-defined function or method.
        The implementation is provided in the project.
        """
        self.function_id = function_id
        self.function_name = function_name
        self.function_code = function_code
        self.start_line_number = start_line_number
        self.end_line_number = end_line_number
        self.file_path = file_path
        self.lined_code = (
            self.attach_relative_line_number()
        )  # code with line number attached

        # Attention: the parse tree is in the context of the whole file
        self.parse_tree_root_node = (
            function_node  # root node of the parse tree of the current function
        )
        self.function_call_site_nodes: Dict[int, Node] = (
            {}
        )  # call site info of user-defined functions
        self.api_call_site_nodes: Dict[int, Node] = {}  # call site info of library APIs

        ## Results of AST node type analysis
        # XXX (ZZ): Parameters may vary in complexity (e.g., regular, variadic, or object-based).
        # To standardize parameter access, we define self._paras as private and provide a getter
        # function to retrieve them.
        self._paras: Optional[Set[Value]] = (
            None  # A optional set of parameters including regular, variadic, and object-based parameters
        )
        self.retvals: Optional[Set[Value]] = None  # A optional set of returned values

        ## Results of intraprocedural control flow analysis
        self.if_statements: Dict[Scope, IfStatement] = {}  # if statement info
        self.loop_statements: Dict[Scope, LoopStatement] = {}  # loop statement info

    def add_para(self, para: Value) -> None:
        """
        Add a parameter to the function.
        :param para: the parameter to be added
        """
        if self._paras is None:
            raise RAAnalysisError(
                f"The parameters of function {self.function_name} has not been analyzed yet. "
                "Please call the analyze function first."
            )
        else:
            self._paras.add(para)

    # TODO (ZZ): add cache to avoid recomputing the parameters.
    # XXX (ZZ): ensure the returned values are new instances, not the original ones
    def paras(self, para_label: Optional[ValueLabel]) -> Set[Value]:
        """
        Get the parameters of the function.
        :param para_label: the label of the parameter, if None, return all parameters
        :return: the parameters of the function
        """
        if self._paras is None:
            raise RAAnalysisError(
                f"The parameters of function {self.function_name} has not been analyzed yet. "
                "Please call the analyze function first."
            )

        if para_label is None:
            return copy.copy(self._paras)
        else:
            assert para_label.is_para(), "para_label should be a parameter label"
            return set(filter(lambda x: x.label == para_label, self._paras))

    def __hash__(self) -> int:
        return hash(
            (
                self.function_name,
                self.function_code,
                self.file_path,
                self.start_line_number,
                self.end_line_number,
            )
        )

    def file_line2function_line(self, file_line: int) -> int:
        """
        Convert the line number in the file to the line number in the function
        """
        return file_line - self.start_line_number + 1

    def attach_relative_line_number(self) -> str:
        """
        Attach line numbers to the function code.
        Line numbers start from 1.
        """
        lined_code = ""
        function_content = "1. " + self.function_code
        line_no = 2
        for ch in function_content:
            if ch == "\n":
                lined_code += "\n" + str(line_no) + ". "
                line_no += 1
            else:
                lined_code += ch
        return lined_code

    def attach_absolute_line_number(self) -> str:
        """
        Attach line numbers to the function code
        Line numbers start from self.start_line_number
        """
        lined_code = ""
        function_content = str(self.start_line_number) + ". " + self.function_code
        line_no = self.start_line_number + 1
        for ch in function_content:
            if ch == "\n":
                lined_code += "\n" + str(line_no) + ". "
                line_no += 1
            else:
                lined_code += ch
        return lined_code
