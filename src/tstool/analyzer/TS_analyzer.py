import sys
from os import path
from pathlib import Path
from typing import List, Tuple, Dict, Set
import tree_sitter
from tree_sitter import Language
from tqdm import tqdm
import networkx as nx
from abc import ABC, abstractmethod

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

from memory.syntactic.function import *
from memory.syntactic.api import *
from memory.syntactic.value import *

class TSAnalyzer(ABC):
    """
    TSAnalyzer class for retrieving necessary facts or functions for llmtools.
    """

    def __init__(
        self,
        code_in_projects: Dict[str, str],
        language_name: str,
    ) -> None:
        """
        Initialize TSAnalyzer with the project source code and language.
        :param code_in_projects: A dictionary mapping file paths to source file contents.
        :param language: The programming language of the source code.
        """
        self.code_in_projects = code_in_projects
        cwd = Path(__file__).resolve().parent.absolute()
        TSPATH = cwd / "../../../lib/build/"
        language_path = TSPATH / "my-languages.so"

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
        self.glb_var_map = {}      # global var info

        self.function_env = {}  
        self.api_env = {}

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


    def parse_project(self) -> None:
        """
        Parse all project files using tree-sitter.
        """
        pbar = tqdm(total=len(self.code_in_projects), desc="Parsing files")
        for file_path in self.code_in_projects:
            pbar.update(1)
            source_code = self.code_in_projects[file_path]
            try:
                tree = self.parser.parse(bytes(source_code, "utf8"))
            except Exception as e:
                print(self.parser)
                print(f"Error parsing {file_path}: {e}")
                exit(0)
            self.extract_function_info(file_path, source_code, tree)
            self.extract_global_info(file_path, source_code, tree)
            self.fileContentDic[file_path] = source_code
        pbar.close()

        pbar = tqdm(total=len(self.functionRawDataDic), desc="Analyzing functions")
        for function_id in self.functionRawDataDic:
            pbar.update(1)
            (name, start_line_number, end_line_number, function_node) = (
                self.functionRawDataDic[function_id]
            )
            file_name = self.functionToFile[function_id]
            file_content = self.fileContentDic[file_name]
            function_code = file_content[function_node.start_byte:function_node.end_byte]
            current_function = Function(
                function_id, name, function_code, start_line_number, end_line_number, function_node, file_name
            )
            current_function = self.extract_meta_data_in_single_function(current_function)
            self.function_env[function_id] = current_function
        pbar.close()


    def analyze_call_graph(self) -> None:
        """
        Compute two kinds of caller-callee relationships:
        1. Between user-defined functions.
        2. Between user-defined functions and library APIs.
        Note that library APIs are collected on the fly
        """
        pbar = tqdm(total=len(self.functionRawDataDic), desc="Analyzing call graphs")
        for function_id in self.function_env:
            pbar.update(1)
            current_function = self.function_env[function_id]
            self.extract_call_graph_edges(current_function)
        pbar.close()

    ###########################################
    # Helper function for project AST parsing #
    ###########################################
    @abstractmethod
    def extract_function_info(self, file_path: str, source_code: str, tree: tree_sitter.Tree) -> None:
        """
        Parse function information from a source file.
        :param file_path: Path of the source file.
        :param source_code: Content of the source file.
        :param tree: Parsed syntax tree.
        """
        pass

    def extract_meta_data_in_single_function(self, current_function: Function) -> Function:
        """
        Extract meta data for a single function.
        :param current_function: The function to be analyzed.
        """
        file_name = self.functionToFile[current_function.function_id]
        file_content = self.fileContentDic[file_name]

        current_function.paras = self.get_parameters_in_single_function(current_function)
        current_function.retsmts = self.get_retstmts_in_single_function(current_function)
        current_function.if_statements = self.get_if_statements(current_function, file_content)
        current_function.loop_statements = self.get_loop_statements(current_function, file_content)
        return current_function

    @abstractmethod
    def extract_global_info(self, file_path: str, source_code: str, tree: tree_sitter.Tree) -> None:
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

        all_call_sites = find_nodes_by_type(current_function.parse_tree_root_node, call_node_type)
        function_call_sites = []
        api_call_sites = []

        for call_site_node in all_call_sites:
            callee_ids = self.get_callee_function_ids_at_callsite(call_site_node, file_content)
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
                arguments = self.get_arguments_at_callsite(call_site_node, file_content)
                callee_name = self.get_callee_name_at_call_site(call_site_node, file_content) 
                tmp_api = API(-1, callee_name, len(arguments))

                # Insert the API into the API environment if it does not exist previously
                for single_api_id in self.api_env:
                    if self.api_env[single_api_id] == tmp_api:
                        api_id = single_api_id
                if api_id == None:
                    self.api_env[len(self.api_env)] = API(len(self.api_env), callee_name, len(arguments))
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
    def get_all_callee_functions(self, function: Function, callee_name: str) -> List[Function]:
        """
        Get all callee functions matching a specific name from the given function.
        :param function: The function to be analyzed.
        :param callee: The name of the callee function.
        """
        while callee_name in self.glb_var_map:
            callee_name = self.glb_var_map[callee_name]
        if function.function_id not in self.function_caller_callee_map:
            return []
        callee_list = []
        for callee_id in self.function_caller_callee_map[function.function_id]:
            if self.function_env[callee_id].function_name == callee_name:
                callee_list.append(self.function_env[callee_id])
        return callee_list
    
    # Helper functions for callees
    ## For library APIs
    def get_all_callee_apis(self, function: Function, callee_name: str, para_num: int) -> List[API]:
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
    def get_callee_name_at_call_site(self, node: tree_sitter.Node, source_code: str) -> str:
        """
        Get the callee name at the call site.
        :param node: The node of the call site.
        :param source_code: The content of the source file.
        :return: The name of the callee function.
        """
        pass

    def get_callee_function_ids_at_callsite(self, call_site_node: tree_sitter.Node, source_code: str) -> List[int]:
        """
        Determine the callee function(s) from a call site.
        :param call_site_node: The node of the call site.
        :param source_code: The content of the source file.
        :return: A list of function ids of the callee functions.
        """
        callee_name = self.get_callee_name_at_call_site(call_site_node, source_code)
        arguments = self.get_arguments_at_callsite(call_site_node, source_code)
        temp_callee_ids = []
        while callee_name in self.glb_var_map:
            callee_name = self.glb_var_map[callee_name]
        if callee_name in self.functionNameToId:
            temp_callee_ids.extend(list(self.functionNameToId[callee_name]))
        # Check parameter count matches the arguments count.
        callee_ids = []
        for callee_id in temp_callee_ids:
            callee = self.function_env[callee_id]
            paras = self.get_parameters_in_single_function(callee)
            if len(paras) == len(arguments):
                callee_ids.append(callee_id)
        return callee_ids
    
    def get_callee_api_ids_at_callsite(self, call_site_node: tree_sitter.Node, source_code: str) -> List[int]:
        """
        Determine the callee api(s) from a call site.
        :param call_site_node: The node of the call site.
        :param source_code: The content of the source file.
        :return: A list of api ids of the callee apis.
        """
        callee_name = self.get_callee_name_at_call_site(call_site_node, source_code)
        arguments = self.get_arguments_at_callsite(call_site_node, source_code)
        callee_ids = []
        while callee_name in self.glb_var_map:
            callee_name = self.glb_var_map[callee_name]
        tmp_api = API(-1, callee_name, len(arguments))
        for api_id in self.api_env:
            if self.api_env[api_id] == tmp_api:
                callee_ids.append(api_id)
        return callee_ids

    @abstractmethod
    def get_callsite_by_callee_name(self, current_function: Function, callee_name: str) -> List[tree_sitter.Node]:
        """
        Find the call site nodes by callee name.
        :param current_function: The function to be analyzed.
        :param callee_name: The name of the callee. Here, the callee can be a function or api
        :return: A list of call site nodes.
        """
        pass

    # Helper functions for arguments
    @abstractmethod
    def get_arguments_at_callsite(self, node: tree_sitter.Node, source_code: str) -> List[str]:
        """
        Get arguments from a call site.
        :param node: The node of the call site.
        :param source_code: The content of the source file.
        :return: A list of arguments.
        """
        pass

    def get_argument_by_index(self, function: Function, callee_name: str, index: int) -> List[Value]:
        """
        Retrieve the argument Value(s) at a given index for a specific callee.
        """
        results = []
        for arg in self.get_arguments_by_callee_name(function, callee_name):
            if arg[2] == index:
                results.append(Value(arg[0], arg[1], ValueLabel.ARG, function.file_name, index))
        return results

    @abstractmethod
    def get_arguments_by_callee_name(self, current_function: Function, callee: str) -> Set[Tuple[str, int, int]]:
        """
        Retrieve the arguments based on callee name from a function.
        :param current_function: The function to be analyzed.
        :param callee: The callee function name.
        :return: A set of tuples (arg_name, line_number, index) for the arguments.
        """
        pass

    # Helper functions for parameters
    @abstractmethod
    def get_parameters_in_single_function(self, current_function: Function) -> Set[Tuple[str, int, int]]:
        """
        Find the parameters of a function.
        :param current_function: The function to be analyzed.
        :return: A set of tuples (para_name, line_number, index) for the parameters.
        """
        pass

    def get_parameter_by_index(self, function: Function, index: int) -> Value:
        """
        Get the parameter Value for the function by its index.
        """
        for para in self.get_parameters_in_single_function(function):
            if para[2] == index:
                return Value(para[0], para[1], ValueLabel.PARA, function.file_name, index)
        return None

    # Helper functions for output values
    def get_output_value_from_callsite(self, function: Function, callee_name: str) -> List[Value]:
        """
        Extract return Value(s) from call sites corresponding to a specific callee.
        """
        results = []
        file_code = self.code_in_projects[function.file_name]
        for call_site_node in self.get_callsite_by_callee_name(function, callee_name):
            name = file_code[call_site_node.start_byte:call_site_node.end_byte]
            line_number = file_code[:call_site_node.start_byte].count("\n") + 1
            results.append(Value(name, line_number, ValueLabel.OUT, function.file_name, 0))
        return results

    # Helper functions for return values
    @abstractmethod
    def get_retstmts_in_single_function(self, current_function: Function) -> List[Tuple[str, int]]:
        """
        Find return statements within a function.
        :param current_function: The function to be analyzed.
        :return: A list of tuples (ret_stmt, line_number) for the return statements.
        """
        pass

    # Control Flow Analysis
    @abstractmethod
    def get_if_statements(self, function: Function, source_code: str) -> Dict[Tuple, Tuple]:
        """
        Identify if-statements within a function.
        :param function: The function to be analyzed.
        :param source_code: The source file content.
        :return: A dictionary mapping (start_line, end_line) to if-statement info.
        """
        pass

    @abstractmethod
    def get_loop_statements(self, function: Function, source_code: str) -> Dict[Tuple, Tuple]:
        """
        Identify loop statements within a function.
        :param function: The function to be analyzed.
        :param source_code: The source file content.
        :return: A dictionary mapping (start_line, end_line) to loop statement info.
        """
        pass

    def check_control_order(self, function: Function, src_line_number: str, sink_line_number: str) -> bool:
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
                true_branch_start_line <= src_line_number_in_function <= true_branch_end_line and
                else_branch_start_line <= sink_line_number_in_function <= else_branch_end_line and
                else_branch_start_line != 0 and else_branch_end_line != 0
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
                    loop_body_start_line <= src_line_number_in_function <= loop_body_end_line and
                    loop_body_start_line <= sink_line_number_in_function <= loop_body_end_line
                ):
                    return True
            return False
        return True

    def check_control_reachability(self, function: Function, src_line_number: str, sink_line_number: str) -> bool:
        """
        Check if control can reach from the source line to the sink line, considering return statements.
        """
        if not self.check_control_order(function, src_line_number, sink_line_number):
            return False
        # TODO: Enhance return statement analysis if needed.
        return True

    # Other helper functions

    def get_node_by_line_number(self, line_number: int) -> List[Tuple[str, tree_sitter.Node]]:
        """
        Find nodes that contain a specific line number.
        """
        code_node_list = []
        for function_id in self.function_env:
            function = self.function_env[function_id]
            if not (function.start_line_number <= line_number <= function.end_line_number):
                continue
            all_nodes = find_all_nodes(function.parse_tree_root_node)
            for node in all_nodes:
                start_line = function.function_code[:node.start_byte].count("\n") + function.start_line_number
                end_line = function.function_code[:node.end_byte].count("\n") + function.start_line_number
                if start_line == end_line == line_number:
                    code_node_list.append((function.function_code, node))
        return code_node_list

    def get_function_from_localvalue(self, value: Value) -> Function:
        """
        Retrieve the function corresponding to a local value.
        """
        file_name = value.file
        for function_id, function in self.function_env.items():
            if function.file_name == file_name:
                if function.start_line_number <= value.line_number <= function.end_line_number:
                    return function
        return None

    def get_content_by_line_number(self, line_number: int, file_name: str) -> str:
        """
        Get the content from a file at the specified line.
        """
        if file_name not in self.code_in_projects:
            return ""
        file_lines = self.code_in_projects[file_name].split("\n")
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

def find_nodes_by_type(root_node: tree_sitter.Node, node_type: str, k=0) -> List[tree_sitter.Node]:
    """
    Recursively find all nodes of a given type.
    """
    nodes = []
    if k > 100:
        return []
    if root_node.type == node_type:
        nodes.append(root_node)
    for child_node in root_node.children:
        nodes.extend(find_nodes_by_type(child_node, node_type, k+1))
    return nodes
