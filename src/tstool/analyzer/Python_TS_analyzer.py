import sys
from os import path
from typing import List, Tuple, Dict, Set
import tree_sitter

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

from .TS_analyzer import *
from memory.syntactic.function import *
from memory.syntactic.value import *


class Python_TSParser(TSParser):
    """
    TSParser class for extracting information from source files using tree-sitter.
    """
    def parse_function_info(self, file_path: str, source_code: str, tree: tree_sitter.Tree) -> None:
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

    def parse_global_info(self, file_path: str, source_code: str, tree: tree_sitter.Tree) -> None:
        """
        Parse the global macro information in a source file.
        :param file_path: The path of the source file.
        :param source_code: The content of the source file.
        :param tree: The parse tree of the source file.
        """
        pass


class Python_TSAnalyzer(TSAnalyzer):
    """
    TSAnalyzer class for retrieving necessary facts or functions for llmtools
    """
    def create_ts_parser(self):
        return Python_TSParser(self.code_in_projects, self.language)
    
    #################################################
    ########## Call Graph Analysis ##################
    #################################################
    def extract_call_graph_edges(self, current_function: Function):
        """
        Extract the call graph edges.
        :param current_function: the function to be analyzed
        """
        # Over-approximate the caller-callee relationship via function names, achieved by find_callee
        file_name = self.ts_parser.functionToFile[current_function.function_id]
        file_content = self.ts_parser.fileContentDic[file_name]

        all_call_sites = find_nodes_by_type(current_function.parse_tree_root_node, "call")
        white_call_sites = []

        for call_site_node in all_call_sites:
            callee_ids = self.get_callee_at_callsite(call_site_node, file_content)
            if len(callee_ids) > 0:
                # Update the call graph
                for callee_id in callee_ids:
                    caller_id = current_function.function_id
                    if caller_id not in self.caller_callee_map:
                        self.caller_callee_map[caller_id] = set([])
                    self.caller_callee_map[caller_id].add(callee_id)
                    if callee_id not in self.callee_caller_map:
                        self.callee_caller_map[callee_id] = set([])
                    self.callee_caller_map[callee_id].add(caller_id)
                white_call_sites.append(call_site_node)
        current_function.call_site_nodes = white_call_sites
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

    #################################################
    ########## AST Node Type Analysis ###############
    #################################################   

    def get_paras_in_single_function(self, current_function: Function) -> Set[Tuple[str, int, int]]:
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

    def get_args_by_callee_name(self, current_function: Function, callee: str) -> Set[Tuple[str, int, int]]:
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

    def get_retstmts_in_single_function(self, current_function: Function) -> List[Tuple[str, int]]:
        """
        Find the return statements in the function.
        :param current_function: the function to be analyzed
        :return: (ret_stmt, line_number) of the return statements
        """
        retstmts = []
        file_content = self.code_in_projects[current_function.file_name]
        retnodes = find_nodes_by_type(current_function.parse_tree_root_node, "return_statement")
        for retnode in retnodes:
            line_number = file_content[:retnode.start_byte].count("\n") + 1
            retstmts.append((file_content[retnode.start_byte:retnode.end_byte], line_number))
        return retstmts

    #################################################
    ########## Control Flow Analysis ################
    #################################################

    def get_if_statements(self, function: Function, source_code: str) -> Dict[Tuple, Tuple]:
        """
        Find the if statements in the Python function.
        :param function: the function to be analyzed
        :param source_code: the content of the file
        :return: a dictionary containing the if statement info and the line number: `(start_line, end_line): info`
        """
        if_statement_nodes = find_nodes_by_type(function.parse_tree_root_node, "if_statement")
        if_statements = {}

        for if_statement_node in if_statement_nodes:
            sub_node_types = if_statement_node.children

            condition_str = source_code[sub_node_types[1].start_byte:sub_node_types[1].end_byte]
            condition_start_line = source_code[: sub_node_types[1].start_byte].count("\n") + 1
            condition_end_line = source_code[: sub_node_types[1].end_byte].count("\n") + 1
            true_branch_start_line = source_code[: sub_node_types[3].start_byte].count("\n") + 1
            true_branch_end_line = source_code[: sub_node_types[3].end_byte].count("\n") + 1

            if "else_clause" in [sub_node.type for sub_node in sub_node_types] or "elif_clause" in [sub_node.type for sub_node in sub_node_types]:
                else_branch_start_line = source_code[: sub_node_types[4].start_byte].count("\n") + 1
                else_branch_end_line = source_code[: if_statement_node.end_byte].count("\n") + 1
            else:
                else_branch_start_line = 0
                else_branch_end_line = 0

            if_statement_start_line = source_code[: if_statement_node.start_byte].count("\n") + 1
            if_statement_end_line = source_code[: if_statement_node.end_byte].count("\n") + 1
            line_scope = (if_statement_start_line, if_statement_end_line)
            info = (
                condition_start_line,
                condition_end_line,
                condition_str,
                (true_branch_start_line, true_branch_end_line),
                (else_branch_start_line, else_branch_end_line),
            )
            if_statements[line_scope] = info
        return if_statements


    def get_loop_statements(self, function: Function, source_code: str) -> Dict[Tuple, Tuple]:
        """
        Find the loop statements in the Python function.
        :param function: the function to be analyzed
        :param source_code: the content of the file
        :return: a dictionary containing the if statement info and the line number: `(start_line, end_line): info`
        """
        loop_statements = {}
        loop_nodes = find_nodes_by_type(function.parse_tree_root_node, "for_statement")
        loop_nodes.extend(find_nodes_by_type(function.parse_tree_root_node, "while_statement"))

        for loop_node in loop_nodes:
            loop_start_line = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end_line = source_code[: loop_node.end_byte].count("\n") + 1

            header_line_start = 0
            header_line_end = 0
            header_str = ""
            loop_body_start_line = 0
            loop_body_end_line = 0

            for loop_child_node in loop_node.children:
                if loop_child_node.type == ":":
                    header_line_start = source_code[: loop_node.start_byte].count("\n") + 1
                    header_line_end = source_code[: loop_child_node.start_byte].count("\n") + 1
                    header_str = source_code[loop_node.start_byte: loop_child_node.start_byte]
                if loop_child_node.type == "block":
                    loop_body_start_line = source_code[: loop_child_node.start_byte].count("\n") + 1
                    loop_body_end_line = source_code[: loop_child_node.end_byte].count("\n") + 1
                    
            loop_statements[(loop_start_line, loop_end_line)] = (
                header_line_start,
                header_line_end,
                header_str,
                loop_body_start_line,
                loop_body_end_line
            )
        return loop_statements
