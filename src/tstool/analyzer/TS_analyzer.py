import sys
from os import path
from pathlib import Path
import copy
import concurrent.futures
from typing import List, Tuple, Dict, Set
from abc import ABC, abstractmethod

import tree_sitter
from tree_sitter import Language
from tqdm import tqdm
import networkx as nx

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

from memory.syntactic.function import *
from memory.syntactic.api import *
from memory.syntactic.value import *


class Parenthesis(Enum):
    LEFT_PAR = -1
    RIGHT_PAR = 1

    def __str__(self) -> str:
        return self.name


class ContextLabel:
    def __init__(
        self,
        file_name: str,
        line_number: int,
        function_id: int,
        parenthesis: Parenthesis,
    ):
        self.file_name = file_name
        self.line_number = line_number
        self.function_id = function_id
        self.parenthesis = parenthesis

    def __str__(self) -> str:
        return f"({self.file_name} {self.line_number} {self.function_id} {self.parenthesis})"


class CallContext:
    def __init__(self, is_backward: bool = True):
        self.context: List[ContextLabel] = []
        self.simplified_context: List[ContextLabel] = []
        self.is_backward = is_backward

    def add_and_check_context(self, label: ContextLabel) -> bool:
        """
        Add a context entry to the context
        :param label: the context label
        :ret True if the context after adding the new context label is in the CFL reachable, False otherwise
        """
        is_CFL_reachable = True

        # Handle empty context case
        if len(self.simplified_context) == 0:
            self.simplified_context.append(label)
            self.context.append(label)
            return is_CFL_reachable

        # Get the top element from the context stack
        top_label = self.get_top_unmatched_context_label()

        # Determine which labels to match based on analysis direction
        first_label = (
            Parenthesis.LEFT_PAR if not self.is_backward else Parenthesis.RIGHT_PAR
        )
        second_label = (
            Parenthesis.RIGHT_PAR if not self.is_backward else Parenthesis.LEFT_PAR
        )

        # Check the label combinations
        if top_label.parenthesis == label.parenthesis:
            self.simplified_context.append(label)
        elif top_label == first_label and label == second_label:
            if (
                top_label.file_name == label.file_name
                and top_label.line_number == label.line_number
                and top_label.function_id == label.function_id
            ):
                self.simplified_context.pop()
            else:
                is_CFL_reachable = False
        else:
            # Other combinations
            self.simplified_context.append(label)

        # Only update context if CFL reachable
        if is_CFL_reachable:
            self.context.append(label)
        return is_CFL_reachable

    def get_top_unmatched_context_label(self) -> ContextLabel:
        """
        Get the top unmatched context label.
        :return: The top unmatched context label.
        """
        if len(self.simplified_context) == 0:
            return None
        return self.simplified_context[-1]

    def __str__(self) -> str:
        """
        Convert the context to a string representation.
        """
        return f"{self.is_backward}" + " -> ".join(
            [str(label) for label in self.context]
        )

    def __eq__(self, other: "CallContext") -> bool:
        return self.__str__() == other.__str__()

    def __hash__(self) -> int:
        # Convert context list to tuple for hashing; assumes that context entries are immutable
        return hash(self.__str__())


class TSAnalyzer(ABC):
    """
    TSAnalyzer class for retrieving necessary facts or functions for llmtools.
    """

    def __init__(
        self,
        code_in_files: Dict[str, str],
        language_name: str,
        max_symbolic_workers_num=10,
    ) -> None:
        """
        Initialize TSAnalyzer with the project source code and language.
        :param code_in_files: A dictionary mapping file paths to source file contents.
        :param language: The programming language of the source code.
        """
        self.code_in_files = code_in_files
        cwd = Path(__file__).resolve().parent.absolute()
        TSPATH = cwd / "../../../lib/build/"
        language_path = TSPATH / "my-languages.so"
        self.max_symbolic_workers_num = max_symbolic_workers_num

        # Initialize tree-sitter parser
        self.parser = tree_sitter.Parser()
        self.language_name = language_name
        if language_name == "C":
            self.language = Language(str(language_path), "c")
        elif language_name == "Cpp":
            self.language = Language(str(language_path), "cpp")
        elif language_name == "Java":
            self.language = Language(str(language_path), "java")
        elif language_name == "Python":
            self.language = Language(str(language_path), "python")
        elif language_name == "Go":
            self.language = Language(str(language_path), "go")
        else:
            raise ValueError("Invalid language setting")
        self.parser.set_language(self.language)

        # Results of parsing
        self.functionRawDataDic = {}
        self.functionNameToId = {}
        self.functionToFile = {}
        self.fileContentDic = {}
        self.glb_var_map = {}  # global var info

        self.function_env: dict[int, Function] = {}
        self.api_env: dict[int, API] = {}

        # Results of call graph analysis
        ## Caller-callee relationship between user-defined functions
        self.function_caller_callee_map = {}
        self.function_callee_caller_map = {}

        ## Caller-callee relationship between user-defined functions and library APIs
        self.function_caller_api_callee_map = {}
        self.api_callee_function_caller_map = {}

        # Analyze stage I: Project AST parsing
        self.parse_project()

        # Analyze stage II: Call graph analysis
        self.analyze_call_graph()
        return

    def _parse_single_file(self, file_path: str, source_code: str) -> Tuple[str, str]:
        """
        Helper function to parse a single file.
        """
        try:
            tree = self.parser.parse(bytes(source_code, "utf8"))
        except Exception as e:
            print(self.parser)
            print(f"Error parsing {file_path}: {e}")
            exit(0)
        # Call user-defined processing.
        self.extract_function_info(file_path, source_code, tree)
        self.extract_global_info(file_path, source_code, tree)
        return file_path, source_code

    def _analyze_single_function(
        self, function_id: int, raw_data: Tuple
    ) -> Tuple[int, "Function"]:
        """
        Helper function to analyze a single function.
        """
        (name, start_line_number, end_line_number, function_node) = raw_data
        file_name = self.functionToFile[function_id]
        file_content = self.fileContentDic[file_name]
        function_code = file_content[function_node.start_byte : function_node.end_byte]
        current_function = Function(
            function_id,
            name,
            function_code,
            start_line_number,
            end_line_number,
            function_node,
            file_name,
        )
        current_function = self.extract_meta_data_in_single_function(current_function)
        return function_id, current_function

    def parse_project(self) -> None:
        """
        Parse all project files using tree-sitter.
        """
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_symbolic_workers_num
        ) as executor:
            futures = {}
            pbar = tqdm(total=len(self.code_in_files), desc="Parsing files")
            for file_path, source_code in self.code_in_files.items():
                # Submit a task for each file.
                future = executor.submit(
                    self._parse_single_file, file_path, source_code
                )
                futures[future] = file_path
            # Collect results.
            for future in concurrent.futures.as_completed(futures):
                file_path, source = future.result()
                self.fileContentDic[file_path] = source
                pbar.update(1)
            pbar.close()

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_symbolic_workers_num
        ) as executor:
            futures = {}
            pbar = tqdm(total=len(self.functionRawDataDic), desc="Analyzing functions")
            for function_id, raw_data in self.functionRawDataDic.items():
                future = executor.submit(
                    self._analyze_single_function, function_id, raw_data
                )
                futures[future] = function_id

            for future in concurrent.futures.as_completed(futures):
                func_id, current_function = future.result()
                self.function_env[func_id] = current_function
                pbar.update(1)
            pbar.close()
        return

    def analyze_call_graph(self) -> None:
        """
        Compute two kinds of caller-callee relationships:
        1. Between user-defined functions.
        2. Between user-defined functions and library APIs.
        Note that library APIs are collected on the fly.
        This method parallelizes the extraction of call graph edges.
        """
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_symbolic_workers_num
        ) as executor:
            futures = {}
            pbar = tqdm(total=len(self.function_env), desc="Analyzing call graphs")
            for function_id, current_function in self.function_env.items():
                future = executor.submit(
                    self.extract_call_graph_edges, current_function
                )
                futures[future] = function_id
            for future in concurrent.futures.as_completed(futures):
                # Optionally, process or log each completed task here.
                pbar.update(1)
            pbar.close()
        return

    ###########################################
    # Helper function for project AST parsing #
    ###########################################
    @abstractmethod
    def extract_function_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """
        Parse function information from a source file.
        :param file_path: Path of the source file.
        :param source_code: Content of the source file.
        :param tree: Parsed syntax tree.
        """
        pass

    def extract_meta_data_in_single_function(
        self, current_function: Function
    ) -> Function:
        """
        Extract meta data for a single function.
        :param current_function: The function to be analyzed.
        """
        file_name = self.functionToFile[current_function.function_id]
        file_content = self.fileContentDic[file_name]

        current_function.paras = self.get_parameters_in_single_function(
            current_function
        )
        current_function.retvals = self.get_return_values_in_single_function(
            current_function
        )
        current_function.if_statements = self.get_if_statements(
            current_function, file_content
        )
        current_function.loop_statements = self.get_loop_statements(
            current_function, file_content
        )
        return current_function

    @abstractmethod
    def extract_global_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """
        Parse macro or global variable information from a source file.
        :param file_path: Path of the source file.
        :param source_code: Content of the source file.
        :param tree: Parsed syntax tree.
        """
        pass

    ###########################################
    # Helper function for call graph analysis #
    ###########################################
    def extract_call_graph_edges(self, current_function: Function) -> None:
        """
        Extract the two kinds of call graph edges for the given function.
        1. Between user-defined functions.
        2. Between user-defined functions and library APIs.
        :param current_function: the function to be analyzed.
        """
        file_name = self.functionToFile[current_function.function_id]
        file_content = self.fileContentDic[file_name]

        call_node_type = None
        if self.language_name == "C" or self.language_name == "Cpp":
            call_node_type = "call_expression"
        elif self.language_name == "Java":
            call_node_type = "method_invocation"
        elif self.language_name == "Python":
            call_node_type = "call"
        elif self.language_name == "Go":
            call_node_type = "call_expression"

        assert call_node_type != None

        all_call_sites = find_nodes_by_type(
            current_function.parse_tree_root_node, call_node_type
        )
        function_call_sites = []
        api_call_sites = []

        for call_site_node in all_call_sites:
            callee_ids = self.get_callee_function_ids_at_callsite(
                current_function, call_site_node
            )
            if len(callee_ids) > 0:
                # Update the caller-callee relationship between user-defined functions
                for callee_id in callee_ids:
                    caller_id = current_function.function_id
                    if caller_id not in self.function_caller_callee_map:
                        self.function_caller_callee_map[caller_id] = set([])
                    self.function_caller_callee_map[caller_id].add(callee_id)
                    if callee_id not in self.function_callee_caller_map:
                        self.function_callee_caller_map[callee_id] = set([])
                    self.function_callee_caller_map[callee_id].add(caller_id)
                function_call_sites.append(call_site_node)
            else:
                api_id = None
                arguments = self.get_arguments_at_callsite(
                    current_function, call_site_node
                )
                callee_name = self.get_callee_name_at_call_site(
                    call_site_node, file_content
                )
                tmp_api = API(-1, callee_name, len(arguments))

                # Insert the API into the API environment if it does not exist previously
                for single_api_id in self.api_env:
                    if self.api_env[single_api_id] == tmp_api:
                        api_id = single_api_id
                if api_id == None:
                    self.api_env[len(self.api_env)] = API(
                        len(self.api_env), callee_name, len(arguments)
                    )
                    api_id = len(self.api_env) - 1

                caller_id = current_function.function_id
                # Update the caller-callee relationship between user-defined functions and library APIs
                if caller_id not in self.function_caller_api_callee_map:
                    self.function_caller_api_callee_map[caller_id] = set([])
                self.function_caller_api_callee_map[caller_id].add(api_id)
                if api_id not in self.api_callee_function_caller_map:
                    self.api_callee_function_caller_map[api_id] = set([])
                self.api_callee_function_caller_map[api_id].add(caller_id)
                api_call_sites.append(call_site_node)

        current_function.function_call_site_nodes = function_call_sites
        current_function.api_call_site_nodes = api_call_sites
        return

    # Helper functions for callers
    def get_all_caller_functions(self, function: Function) -> List[Function]:
        """
        Get all caller functions for the provided function.
        """
        callee_id = function.function_id
        if callee_id not in self.function_callee_caller_map:
            return []
        caller_ids = self.function_callee_caller_map[function.function_id]
        return [self.function_env[caller_id] for caller_id in caller_ids]

    # Helper functions for callees
    ## For user-defined functions
    def get_all_callee_functions(self, function: Function) -> List[Function]:
        """
        Get all callee functions matching a specific name from the given function.
        :param function: The function to be analyzed.
        """
        # TODO: @jinyao. We need to find a more elegant way to expand the macro
        # while callee_name in self.glb_var_map:
        #     callee_name = self.glb_var_map[callee_name]
        if function.function_id not in self.function_caller_callee_map:
            return []
        callee_ids = self.function_caller_callee_map[function.function_id]
        return [self.function_env[callee_id] for callee_id in callee_ids]

    def get_all_transitive_caller_functions(
        self, function: Function, max_depth=1000
    ) -> List[Function]:
        """
        Get all transitive caller functions for the provided function.
        """
        if max_depth == 0:
            return []
        if function.function_id not in self.function_callee_caller_map:
            return []
        caller_ids = self.function_callee_caller_map[function.function_id]
        caller_functions = [self.function_env[caller_id] for caller_id in caller_ids]
        for caller_function in caller_functions:
            caller_functions.extend(
                self.get_all_transitive_caller_functions(caller_function, max_depth - 1)
            )
        caller_functions = list(
            {function.function_id: function for function in caller_functions}.values()
        )
        return caller_functions

    def get_all_transitive_callee_functions(
        self, function: Function, max_depth, visited=None
    ) -> List[Function]:
        """
        Get all transitive callee functions for the provided function.
        """
        if max_depth == 0:
            return []

        if visited is None:
            visited = set()

        if function.function_id in visited:
            return []

        visited.add(function.function_id)

        if function.function_id not in self.function_caller_callee_map:
            return []
        callee_ids = self.function_caller_callee_map[function.function_id]
        callee_functions = [self.function_env[callee_id] for callee_id in callee_ids]
        for callee_function in callee_functions:
            callee_functions.extend(
                self.get_all_transitive_callee_functions(
                    callee_function, max_depth - 1, visited
                )
            )
        callee_functions = list(
            {function.function_id: function for function in callee_functions}.values()
        )
        return callee_functions

    # Helper functions for callees
    ## For library APIs
    def get_all_callee_apis(
        self, function: Function, callee_name: str, para_num: int
    ) -> List[API]:
        """
        Get all callee apis matching a specific name from the given function.
        :param function: The function to be analyzed.
        :param callee: The name of the callee API.
        :param para_num: The number of parameters of the callee API.
        """
        callee_list = []
        for callee_api_id in self.function_caller_api_callee_map[function.function_id]:
            if self.api_env[callee_list] == API(-1, callee_name, para_num):
                callee_list.append(self.api_env[callee_list])
        return callee_list

    @abstractmethod
    def get_callee_name_at_call_site(
        self, node: tree_sitter.Node, source_code: str
    ) -> str:
        """
        Get the callee name at the call site.
        :param node: The node of the call site.
        :param source_code: The content of the source file.
        :return: The name of the callee function.
        """
        pass

    def get_callee_function_ids_at_callsite(
        self, current_function: Function, call_site_node: tree_sitter.Node
    ) -> List[int]:
        """
        Determine the callee function(s) from a call site.
        :param current_function: The function to be analyzed.
        :param call_site_node: The node of the call site.
        :return: A list of function ids of the callee functions.
        """
        file_name = current_function.file_path
        source_code = self.code_in_files[file_name]
        callee_name = self.get_callee_name_at_call_site(call_site_node, source_code)
        arguments = self.get_arguments_at_callsite(current_function, call_site_node)
        temp_callee_ids = []
        # while callee_name in self.glb_var_map:
        #     callee_name = self.glb_var_map[callee_name]
        if callee_name in self.functionNameToId:
            temp_callee_ids.extend(list(self.functionNameToId[callee_name]))
        # Check parameter count matches the arguments count.
        callee_ids = []
        for callee_id in temp_callee_ids:
            callee = self.function_env[callee_id]
            paras = callee.paras
            if len(paras) == len(arguments):
                callee_ids.append(callee_id)
        return callee_ids

    def get_callee_api_ids_at_callsite(
        self, current_function: Function, call_site_node: tree_sitter.Node
    ) -> List[int]:
        """
        Determine the callee api(s) from a call site.
        :param current_function: The function to be analyzed.
        :param call_site_node: The node of the call site.
        :return: A list of api ids of the callee apis.
        """
        file_name = current_function.file_path
        source_code = self.code_in_files[file_name]
        callee_name = self.get_callee_name_at_call_site(call_site_node, source_code)
        arguments = self.get_arguments_at_callsite(current_function, call_site_node)
        callee_ids = []
        # while callee_name in self.glb_var_map:
        #     callee_name = self.glb_var_map[callee_name]
        tmp_api = API(-1, callee_name, len(arguments))
        for api_id in self.api_env:
            if self.api_env[api_id] == tmp_api:
                callee_ids.append(api_id)
        return callee_ids

    @abstractmethod
    def get_callsites_by_callee_name(
        self, current_function: Function, callee_name: str
    ) -> List[tree_sitter.Node]:
        """
        Find the call site nodes by callee name.
        :param current_function: The function to be analyzed.
        :param callee_name: The name of the callee. Here, the callee can be a function or api
        :return: A list of call site nodes.
        """
        pass

    # Helper functions for arguments
    @abstractmethod
    def get_arguments_at_callsite(
        self, current_function: Function, call_site_node: tree_sitter.Node
    ) -> Set[Value]:
        """
        Get arguments from a call site in a function.
        :param current_function: the function to be analyzed
        :param call_site_node: the node of the call site
        :return: the arguments
        """
        pass

    # Helper functions for parameters
    @abstractmethod
    def get_parameters_in_single_function(
        self, current_function: Function
    ) -> Set[Value]:
        """
        Find the parameters of a function.
        :param current_function: The function to be analyzed.
        :return: A set of parameters as values
        """
        pass

    # Helper functions for output values
    def get_output_value_at_callsite(
        self, current_function: Function, call_site_node: tree_sitter.Node
    ) -> Value:
        """
        Get the output value from a call site.
        :param current_function: The function to be analyzed.
        :param call_site_node: The node of the call site.
        :return: The output value.
        """
        file_code = self.code_in_files[current_function.file_path]
        name = file_code[call_site_node.start_byte : call_site_node.end_byte]
        line_number = file_code[: call_site_node.start_byte].count("\n") + 1
        output_value = Value(
            name, line_number, ValueLabel.OUT, current_function.file_path, -1
        )
        return output_value

    # Helper functions for return values
    @abstractmethod
    def get_return_values_in_single_function(
        self, current_function: Function
    ) -> Set[Value]:
        """
        Find the return values of a function.
        :param current_function: The function to be analyzed.
        :return: A set of return values as values
        """
        pass

    # Control Flow Analysis
    @abstractmethod
    def get_if_statements(
        self, function: Function, source_code: str
    ) -> Dict[Tuple, Tuple]:
        """
        Identify if-statements within a function.
        :param function: The function to be analyzed.
        :param source_code: The source file content.
        :return: A dictionary mapping (start_line, end_line) to if-statement info.
        """
        pass

    @abstractmethod
    def get_loop_statements(
        self, function: Function, source_code: str
    ) -> Dict[Tuple, Tuple]:
        """
        Identify loop statements within a function.
        :param function: The function to be analyzed.
        :param source_code: The source file content.
        :return: A dictionary mapping (start_line, end_line) to loop statement info.
        """
        pass

    def check_control_order(
        self, function: Function, src_line_number: str, sink_line_number: str
    ) -> bool:
        """
        Check if the source line could execute before the sink line.
        """
        src_line_number_in_function = src_line_number
        sink_line_number_in_function = sink_line_number

        if src_line_number_in_function == sink_line_number_in_function:
            return True

        for if_statement_start_line, if_statement_end_line in function.if_statements:
            (
                _,
                _,
                _,
                (true_branch_start_line, true_branch_end_line),
                (else_branch_start_line, else_branch_end_line),
            ) = function.if_statements[(if_statement_start_line, if_statement_end_line)]
            if (
                true_branch_start_line
                <= src_line_number_in_function
                <= true_branch_end_line
                and else_branch_start_line
                <= sink_line_number_in_function
                <= else_branch_end_line
                and else_branch_start_line != 0
                and else_branch_end_line != 0
            ):
                return False

        if src_line_number_in_function > sink_line_number_in_function:
            for loop_start_line, loop_end_line in function.loop_statements:
                (
                    _,
                    _,
                    _,
                    loop_body_start_line,
                    loop_body_end_line,
                ) = function.loop_statements[(loop_start_line, loop_end_line)]
                if (
                    loop_body_start_line
                    <= src_line_number_in_function
                    <= loop_body_end_line
                    and loop_body_start_line
                    <= sink_line_number_in_function
                    <= loop_body_end_line
                ):
                    return True
            return False
        return True

    def check_control_reachability(
        self, function: Function, src_line_number: str, sink_line_number: str
    ) -> bool:
        """
        Check if control can reach from the source line to the sink line, considering return statements.
        """
        if not self.check_control_order(function, src_line_number, sink_line_number):
            return False
        # TODO: Enhance return statement analysis if needed.
        return True

    # Other helper functions

    def get_node_by_line_number(
        self, line_number: int
    ) -> List[Tuple[str, tree_sitter.Node]]:
        """
        Find nodes that contain a specific line number.
        """
        code_node_list = []
        for function_id in self.function_env:
            function = self.function_env[function_id]
            if not (
                function.start_line_number <= line_number <= function.end_line_number
            ):
                continue
            all_nodes = find_all_nodes(function.parse_tree_root_node)
            for node in all_nodes:
                start_line = (
                    function.function_code[: node.start_byte].count("\n")
                    + function.start_line_number
                )
                end_line = (
                    function.function_code[: node.end_byte].count("\n")
                    + function.start_line_number
                )
                if start_line == end_line == line_number:
                    code_node_list.append((function.function_code, node))
        return code_node_list

    def get_function_from_localvalue(self, value: Value) -> Function:
        """
        Retrieve the function corresponding to a local value.
        """
        file_name = value.file
        for function_id, function in self.function_env.items():
            if function.file_path == file_name:
                if (
                    function.start_line_number
                    <= value.line_number
                    <= function.end_line_number
                ):
                    return function
        return None

    def get_content_by_line_number(self, line_number: int, file_name: str) -> str:
        """
        Get the content from a file at the specified line.
        """
        if file_name not in self.code_in_files:
            return ""
        file_lines = self.code_in_files[file_name].split("\n")
        if line_number > len(file_lines):
            return ""
        return file_lines[line_number - 1]


# Utility functions for AST node type maching


def find_all_nodes(root_node: tree_sitter.Node) -> List[tree_sitter.Node]:
    """
    Recursively find all nodes in the tree starting at root_node.
    """
    if root_node is None:
        return []
    nodes = [root_node]
    for child_node in root_node.children:
        nodes.extend(find_all_nodes(child_node))
    return nodes


def find_nodes_by_type(
    root_node: tree_sitter.Node, node_type: str, k=0
) -> List[tree_sitter.Node]:
    """
    Recursively find all nodes of a given type.
    """
    nodes = []
    if k > 100:
        return []
    if root_node.type == node_type:
        nodes.append(root_node)
    for child_node in root_node.children:
        nodes.extend(find_nodes_by_type(child_node, node_type, k + 1))
    return nodes
