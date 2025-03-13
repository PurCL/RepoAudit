import sys
from os import path
from typing import List, Tuple, Dict, Set
import tree_sitter

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

from .TS_analyzer import *
from memory.syntactic.function import *
from memory.syntactic.value import *

class Python_TSAnalyzer(TSAnalyzer):
    """
    TSAnalyzer for Python source files using tree-sitter.
    Implements Python-specific parsing and analysis.
    """

    def extract_function_info(self, file_path: str, source_code: str, tree: tree_sitter.Tree) -> None:
        """
        Parse the function information in a source file.
        :param file_path: The path of the source file.
        :param source_code: The content of the source file.
        :param tree: The parse tree of the source file.
        """
        all_function_header_nodes = find_nodes_by_type(tree.root_node, "function_definition")      
    
        for node in all_function_header_nodes:
            function_name = ""
            for sub_node in node.children:
                if sub_node.type == "identifier":
                    function_name = source_code[sub_node.start_byte:sub_node.end_byte]
                    break

            if function_name == "":
                continue
            
            start_line_number = source_code[: node.start_byte].count("\n") + 1
            end_line_number = source_code[: node.end_byte].count("\n") + 1
            function_id = len(self.functionRawDataDic) + 1
            
            self.functionRawDataDic[function_id] = (
                function_name,
                start_line_number,
                end_line_number,
                node
            )
            self.functionToFile[function_id] = file_path

            if function_name not in self.functionNameToId:
                self.functionNameToId[function_name] = set([])
            self.functionNameToId[function_name].add(function_id)
        return   

    def extract_global_info(self, file_path: str, source_code: str, tree: tree_sitter.Tree) -> None:
        """
        Parse global variable information from a Python source file.
        For Python, this may include module-level variables.
        Currently not implemented.
        """
        # TODO: Add global variable analysis if needed.
        return

    def get_callee_name_at_call_site(self, node: tree_sitter.Node, source_code: str) -> str:
        """
        Get the callee name at the call site.
        :param node: the node of the call site
        :param source_code: the content of the file
        """
        function_name = ""
        for sub_node in node.children:
            if sub_node.type == "identifier":
                function_name = source_code[sub_node.start_byte:sub_node.end_byte]
                break
            if sub_node.type == "attribute":
                for sub_sub_node in sub_node.children:
                    if sub_sub_node.type == "identifier":
                        function_name = source_code[sub_sub_node.start_byte:sub_sub_node.end_byte]
                break
        return function_name

    def get_callsite_by_callee_name(self, current_function: Function, callee_name: str) -> List[tree_sitter.Node]:
        """
        Find the call sites by the callee function name.
        :param current_function: the function to be analyzed
        :param callee_name: the callee function name
        """
        results = []
        file_content = self.code_in_projects[current_function.file_name]
        call_site_nodes = find_nodes_by_type(current_function.parse_tree_root_node, "call")
        for call_site in call_site_nodes:
            if self.get_callee_name_at_call_site(call_site, file_content) == callee_name:
                results.append(call_site)
                break
        return results

    def get_arguments_at_callsite(self, node: tree_sitter.Node, source_code: str) -> List[str]:
        """
        Get arguments at the call site.
        :param node: the node of the call site
        :param source_code: the content of the file
        """
        arguments = []
        for sub_node in node.children:
            if sub_node.type == "argument_list":
                arg_list = sub_node.children[1:-1]
                for element in arg_list:
                    if element.type != ",":
                        arguments.append(source_code[element.start_byte:element.end_byte])
        return arguments

    def get_arguments_by_callee_name(self, current_function: Function, callee: str) -> Set[Tuple[str, int, int]]:
        """
        Find the arguments of the callee function.
        :param current_function: the function to be analyzed
        :param callee: the callee function name
        :return: (arg_name, line_number, index) of the arguments
        """
        args = set([])
        file_content = self.ts_parser.fileContentDic[current_function.file_name]
        call_site_nodes = self.get_callsite_by_callee_name(current_function, callee)
        for call_site in call_site_nodes:
            for child in call_site.children:
                if child.type == "argument_list":
                    arg_list = child.children[1:-1]
                    index = 0
                    for element in arg_list:
                        if element.type != ",":
                            line_number = file_content[:element.start_byte].count("\n") + 1
                            arg_name = file_content[element.start_byte:element.end_byte]
                            args.add((arg_name, line_number, index))
                            index += 1
                    break
        return args
    
    def get_parameters_in_single_function(self, current_function: Function) -> Set[Tuple[str, int, int]]:
        """
        Find the parameters of the function.
        :param current_function: the function to be analyzed
        :return: (para_name, line_number, index) of the parameters
        """
        paras = set([])
        file_content = self.code_in_projects[current_function.file_name]
        parameters = find_nodes_by_type(current_function.parse_tree_root_node, "parameters")
        index = 0
        for parameter_node in parameters:
            parameter_name = ""
            for sub_node in parameter_node.children:
                for sub_node in find_nodes_by_type(sub_node, "identifier"):      
                    parameter_name = file_content[sub_node.start_byte:sub_node.end_byte]
                    break
            if parameter_name != "" and parameter_name != "self":
                line_number = file_content[:sub_node.start_byte].count("\n") + 1
                paras.add((parameter_name, line_number, index))
                index += 1
        return paras

    def get_retstmts_in_single_function(self, current_function: Function) -> List[Tuple[str, int]]:
        """
        Find return statements in the Python function.
        """
        retstmts = []
        file_content = self.code_in_projects[current_function.file_name]
        return_nodes = find_nodes_by_type(current_function.parse_tree_root_node, "return_statement")
        for node in return_nodes:
            line_number = file_content[:node.start_byte].count("\n") + 1
            retstmts.append((file_content[node.start_byte:node.end_byte], line_number))
        return retstmts

    def get_if_statements(self, function: Function, source_code: str) -> Dict[Tuple, Tuple]:
        """
        Identify if-statements in the Python function.
        This is a simplified analysis for illustrative purposes.
        """
        if_nodes = find_nodes_by_type(function.parse_tree_root_node, "if_statement")
        if_statements = {}
        for node in if_nodes:
            start_line = source_code[:node.start_byte].count("\n") + 1
            end_line = source_code[:node.end_byte].count("\n") + 1
            # For Python, a detailed analysis would require inspecting the condition and body.
            info = (start_line, end_line, "", (end_line, end_line), (0, 0))
            if_statements[(start_line, end_line)] = info
        return if_statements

    def get_loop_statements(self, function: Function, source_code: str) -> Dict[Tuple, Tuple]:
        """
        Identify loop statements (for and while) in the Python function.
        """
        loops = {}
        loop_nodes = find_nodes_by_type(function.parse_tree_root_node, "for_statement")
        loop_nodes.extend(find_nodes_by_type(function.parse_tree_root_node, "while_statement"))
        for node in loop_nodes:
            start_line = source_code[:node.start_byte].count("\n") + 1
            end_line = source_code[:node.end_byte].count("\n") + 1
            # Simplified header and body analysis.
            loops[(start_line, end_line)] = (start_line, start_line, "", start_line, end_line)
        return loops
