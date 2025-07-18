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
from memory.syntactic.value import *


class TSParser(ABC):
    """
    BaseParser class providing a common interface for source code parsing using tree-sitter.
    """

    def __init__(self, code_in_projects: Dict[str, str], language_setting: str) -> None:
        """
        Initialize the parser with project source code and language setting.
        :param code_in_projects: A dictionary containing source file contents.
        :param language_setting: Programming language for parsing.
        """
        self.code_in_projects = code_in_projects
        self.language_setting = language_setting

        self.functionRawDataDic = {}
        self.functionNameToId = {}
        self.functionToFile = {}
        self.fileContentDic = {}
        self.glb_var_map = {}

        cwd = Path(__file__).resolve().parent.absolute()
        TSPATH = cwd / "../../../lib/build/"
        language_path = TSPATH / "my-languages.so"

        # Initialize the parser
        self.parser = tree_sitter.Parser()

        # initilize the language according to language_setting
        if language_setting == "C":
            self.language = Language(str(language_path), "c")
        elif language_setting == "Cpp":
            self.language = Language(str(language_path), "cpp")
        elif language_setting == "Java":
            self.language = Language(str(language_path), "java")
        elif language_setting == "Python":
            self.language = Language(str(language_path), "python")
        elif language_setting == "Go":
            self.language = Language(str(language_path), "go")
        else:
            raise ValueError("Invalid language setting")

        self.parser.set_language(self.language)

    @abstractmethod
    def parse_function_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """
        Parse function information from a source file.
        :param file_path: Path of the source file.
        :param source_code: Content of the source file.
        :param tree: Parsed syntax tree.
        """
        pass

    @abstractmethod
    def parse_global_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """
        Parse macro or global variable information from a source file.
        :param file_path: Path of the source file.
        :param source_code: Content of the source file.
        :param tree: Parsed syntax tree.
        """
        pass

    def parse_project(self) -> None:
        """
        Parse the project.
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
            self.parse_function_info(file_path, source_code, tree)
            self.parse_global_info(file_path, source_code, tree)
            self.fileContentDic[file_path] = source_code
        return


class TSAnalyzer(ABC):
    """
    TSAnalyzer class for retrieving necessary facts or functions for llmtools
    """

    def __init__(
        self,
        code_in_projects: Dict[str, str],
        language: str,
    ) -> None:
        """
        Initialize TSParser with the project path.
        :param code_in_projects: A dictionary mapping file paths of source files to their contents
        :param language: The programming language of the source code
        """
        self.code_in_projects = code_in_projects
        self.language = language
        self.ts_parser = self.create_ts_parser()
        self.ts_parser.parse_project()

        # Each funcntion in the environments maintains the local meta data, including
        # (1) AST node type analysis
        # (2) intraprocedural control flow analysis
        self.environment = {}

        # Macro variable map
        self.glb_var_map = self.ts_parser.glb_var_map

        # Results of call graph analysis
        self.caller_callee_map = {}
        self.callee_caller_map = {}
        self.call_graph = nx.DiGraph()

        pbar = tqdm(
            total=len(self.ts_parser.functionRawDataDic), desc="Analyzing functions"
        )
        for function_id in self.ts_parser.functionRawDataDic:
            pbar.update(1)
            (name, start_line_number, end_line_number, function_node) = (
                self.ts_parser.functionRawDataDic[function_id]
            )
            file_name = self.ts_parser.functionToFile[function_id]
            file_content = self.ts_parser.fileContentDic[file_name]
            function_code = file_content[
                function_node.start_byte : function_node.end_byte
            ]
            current_function = Function(
                function_id,
                name,
                function_code,
                start_line_number,
                end_line_number,
                function_node,
                file_name,
            )
            current_function = self.extract_meta_data_in_single_function(
                current_function
            )
            self.environment[function_id] = current_function
        pbar.close()

        pbar = tqdm(
            total=len(self.ts_parser.functionRawDataDic), desc="Analyzing call graphs"
        )
        for function_id in self.environment:
            pbar.update(1)
            current_function = self.environment[function_id]
            self.extract_call_graph_edges(current_function)
        pbar.close()

        # initialize call graph
        for caller_id in self.caller_callee_map:
            for callee_id in self.caller_callee_map[caller_id]:
                self.call_graph.add_edge(caller_id, callee_id)
        return

    @abstractmethod
    def create_ts_parser(self) -> TSParser:
        """
        Create a TSParser object.
        """
        pass

    def extract_meta_data_in_single_function(
        self, current_function: Function
    ) -> Function:
        """
        Extract meta data in a single function
        :param current_function: the function to be analyzed
        :param file_content: the content of the file
        """
        file_name = self.ts_parser.functionToFile[current_function.function_id]
        file_content = self.ts_parser.fileContentDic[file_name]

        # AST node type analysis
        current_function.paras = self.get_paras_in_single_function(current_function)
        current_function.retsmts = self.get_retstmts_in_single_function(
            current_function
        )

        # Intraprocedural control flow analysis
        current_function.if_statements = self.get_if_statements(
            current_function,
            file_content,
        )

        current_function.loop_statements = self.get_loop_statements(
            current_function,
            file_content,
        )

        return current_function

    #################################################
    ########## Call Graph Analysis ##################
    #################################################
    @abstractmethod
    def extract_call_graph_edges(self, current_function: Function) -> None:
        """
        Extract the call graph edges.
        :param current_function: the function to be analyzed
        """
        pass

    @abstractmethod
    def get_callee_name_at_call_site(
        self, node: tree_sitter.Node, source_code: str
    ) -> str:
        """
        Get the callee name at the call site.
        :param node: the node of the call site
        :param source_code: the content of the file
        :param language: the language of the source code
        :return: the name of the callee function
        """
        pass

    @abstractmethod
    def get_callsite_by_callee_name(
        self, current_function: Function, callee_name: str
    ) -> List[tree_sitter.Node]:
        """
        Find the call site by callee name.
        :param current_function: the function to be analyzed
        :param callee_name: the name of the callee function
        :return: a list of call site nodes
        """
        pass

    @abstractmethod
    def get_arguments_at_callsite(
        self, node: tree_sitter.Node, source_code: str
    ) -> List[str]:
        """
        Get arguments at the call site.
        :param node: the node of the call site
        :param source_code: the content of the file
        :return: a list of arguments
        """
        pass

    def get_callee_at_callsite(
        self, call_site_node: tree_sitter.Node, source_code: str
    ) -> List[int]:
        """
        Find the callee function of the call site.
        :param file_content: the content of the file
        :param call_site_node: the node of the call site
        :return: a list of function ids of the callee functions
        """
        callee_name = self.get_callee_name_at_call_site(call_site_node, source_code)
        arguments = self.get_arguments_at_callsite(call_site_node, source_code)
        temp_callee_ids = []
        # support macro defination
        while callee_name in self.ts_parser.glb_var_map:
            callee_name = self.ts_parser.glb_var_map[callee_name]
        if callee_name in self.ts_parser.functionNameToId:
            temp_callee_ids.extend(list(self.ts_parser.functionNameToId[callee_name]))
        # check parameter number and the argument number
        callee_ids = []
        for callee_id in temp_callee_ids:
            callee = self.environment[callee_id]
            paras = self.get_paras_in_single_function(callee)
            if len(paras) == len(arguments):
                callee_ids.append(callee_id)
        return callee_ids

    def get_all_caller_functions(self, function: Function) -> List[Function]:
        """
        Get the caller function of the function.
        """
        callee_id = function.function_id
        if callee_id not in self.callee_caller_map.keys():
            return []
        caller_ids = self.callee_caller_map[function.function_id]
        caller = [self.environment[caller_id] for caller_id in caller_ids]
        return caller

    def get_all_callee_functions(
        self, function: Function, callee: str
    ) -> List[Function]:
        """
        Get the callee function of the function with name `callee`.
        :param function: the function to be analyzed
        :param callee: the name of the callee function
        """
        while callee in self.ts_parser.glb_var_map:
            callee = self.ts_parser.glb_var_map[callee]
        if function.function_id not in self.caller_callee_map.keys():
            return []
        callee_list = []
        for callee_id in self.caller_callee_map[function.function_id]:
            if self.environment[callee_id].function_name == callee:
                callee_list.append(self.environment[callee_id])
        return callee_list

    #################################################
    ########## AST Node Type Analysis ###############
    #################################################

    @abstractmethod
    def get_paras_in_single_function(
        self, current_function: Function
    ) -> Set[Tuple[str, int, int]]:
        """
        Find the parameters of the function.
        :param current_function: the function to be analyzed
        :return: (para_name, line_number, index) of the parameters
        """
        pass

    @abstractmethod
    def get_args_by_callee_name(
        self, current_function: Function, callee: str
    ) -> Set[Tuple[str, int, int]]:
        """
        Find the arguments of the callee function.
        :param current_function: the function to be analyzed
        :param callee: the callee function name
        :return: (arg_name, line_number, index) of the arguments
        """
        pass

    @abstractmethod
    def get_retstmts_in_single_function(
        self, current_function: Function
    ) -> List[Tuple[str, int]]:
        # TODO: Need to be polished along with Function class
        # We need to track multiple return values, especially for Python and Go.
        """
        Find the return statements in the function.
        :param current_function: the function to be analyzed
        :return: (ret_stmt, line_number) of the return statements
        """

    #################################################
    ########## Control Flow Analysis ################
    #################################################

    @abstractmethod
    def get_if_statements(
        self, function: Function, source_code: str
    ) -> Dict[Tuple, Tuple]:
        """
        Find the if statements in the function.
        :param function: the function to be analyzed
        :param source_code: the content of the file
        :return: a dictionary containing the if statement info and the line number: `(start_line, end_line): info`
        """
        pass

    @abstractmethod
    def get_loop_statements(
        self, function: Function, source_code: str
    ) -> Dict[Tuple, Tuple]:
        """
        Find the loop statements in the function.
        :param function: the function to be analyzed
        :param source_code: the content of the file
        :return: a dictionary containing the if statement info and the line number: `(start_line, end_line): info`
        """

    #################################################
    ########## Control Order Analysis ################
    #################################################
    def check_control_order(
        self, function: Function, src_line_number: str, sink_line_number: str
    ) -> bool:
        """
        If the function return True, the line src_line_number may be execeted before the line sink_line_number.
        The semantics of return statements are not considered.
        This is an over-approximation of the control order.
        """
        src_line_number_in_function = src_line_number
        sink_line_number_in_function = sink_line_number

        if src_line_number_in_function == sink_line_number_in_function:
            return True

        # Consider branches, return false if src and sink in different branches
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

        # Consider loops
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

    #######################################################
    ########## Control reachability Analysis ##############
    #######################################################
    def check_control_reachability(
        self, function: Function, src_line_number: str, sink_line_number: str
    ) -> bool:
        """
        If the function return True, the line src_line_number may be execeted before the line sink_line_number.
        The semantics of return statements are considered.
        This is an over-approximation of the control reachability.
        """
        if (
            self.check_control_order(function, src_line_number, sink_line_number)
            is False
        ):
            return False

        # TODO: Temporarily disable the return satement check
        # for retstmt, retstmt_line_number in function.retsmts:
        #     if self.check_control_order(function, src_line_number, retstmt_line_number) and \
        #         not self.check_control_order(function, sink_line_number, retstmt_line_number):
        #         return False
        return True

    #################################################
    ########## AST visitor utility ##################
    #################################################
    def get_node_by_line_number(
        self, line_number: int
    ) -> List[Tuple[str, tree_sitter.Node]]:
        """
        Find the node that contains the specific line number
        :param line_number: the line number to be searched
        """
        code_node_list = []
        for function_id in self.environment:
            function = self.environment[function_id]
            if (
                not function.start_line_number
                <= line_number
                <= function.end_line_number
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

    #################################################
    ############# AST selector utility ##############
    #################################################
    def get_function_from_localvalue(self, value: Value) -> Function:
        """
        Get the function from the local value.
        """
        file_name = value.file
        for function_id, function in self.environment.items():
            if function.file_name == file_name:
                if (
                    function.start_line_number
                    <= value.line_number
                    <= function.end_line_number
                ):
                    return function
        return None

    def get_parameter_by_index(self, function: Function, index: int) -> Value:
        """
        Get the parameter of the function with index `index`.
        :param function: the function to be analyzed
        :param index: the index of the parameter, starting from 0
        """
        for para in self.get_paras_in_single_function(function):
            if para[2] == index:
                return Value(
                    para[0], para[1], ValueLabel.PARA, function.file_name, index
                )
        return None

    def get_argument_by_index(
        self, function: Function, callee_name: str, index: int
    ) -> List[Value]:
        """
        Get the argument by callee_name and index.
        :param function: the function to be analyzed
        :param callee_name: the name of the callee function
        :param index: the index of the argument, starting from 0
        """
        results = []
        for arg in self.get_args_by_callee_name(function, callee_name):
            if arg[2] == index:
                results.append(
                    Value(arg[0], arg[1], ValueLabel.ARG, function.file_name, index)
                )
        return results

    def get_content_by_line_number(self, line_number: int, file_name: str) -> str:
        """
        Get the content at `line_number` in `file`.
        """
        if file_name not in self.code_in_projects:
            return ""
        file_code = self.code_in_projects[file_name]
        file_lines = file_code.split("\n")
        if line_number > len(file_lines):
            return ""
        return file_lines[line_number - 1]

    def get_return_value_from_callsite(
        self, function: Function, callee_name: str
    ) -> List[Value]:
        """
        Get the return value from the call site.
        :param function: the function to be analyzed
        :param callee_name: the name of the callee function
        """
        results = []
        file_code = self.code_in_projects[function.file_name]
        for call_site_node in self.get_callsite_by_callee_name(function, callee_name):
            name = file_code[call_site_node.start_byte : call_site_node.end_byte]
            line_number = file_code[: call_site_node.start_byte].count("\n") + 1

            # TODO: TO BE Polished. @Chengpeng.
            # We need to extract multiple return values for each return statement and maintain their indexes starting from 0.
            results.append(
                Value(name, line_number, ValueLabel.OUT, function.file_name, 0)
            )
        return results


#################################################
############# Helper functions ##################
#################################################
def find_all_nodes(root_node: tree_sitter.Node) -> List[tree_sitter.Node]:
    """
    Find all the nodes in the parse tree
    :param root_node: the root node of the parse tree
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
    Find all the nodes with the specific type in the parse tree
    :param root_node: the root node of the parse tree
    :param node_type: the type of the nodes to be found
    """
    nodes = []
    if k > 100:
        return []
    if root_node.type == node_type:
        nodes.append(root_node)
    for child_node in root_node.children:
        nodes.extend(find_nodes_by_type(child_node, node_type, k + 1))
    return nodes
