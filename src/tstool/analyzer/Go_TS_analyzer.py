import sys
from os import path
from typing import List, Tuple, Dict, Set
import tree_sitter

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

from .TS_analyzer import *
from memory.syntactic.function import *
from memory.syntactic.value import *


class Go_TSParser(TSParser):
    """
    TSParser class for extracting information from source files using tree-sitter.
    """

    def parse_function_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """
        Parse the function information in a source file.
        :param file_path: The path of the source file.
        :param source_code: The content of the source file.
        :param tree: The parse tree of the source file.
        """
        assert self.language_setting == "Go"
        all_function_nodes = find_nodes_by_type(tree.root_node, "function_declaration")
        all_method_nodes = find_nodes_by_type(tree.root_node, "method_declaration")
        all_function_nodes.extend(all_method_nodes)

        for function_node in all_function_nodes:
            function_name = ""
            for sub_node in function_node.children:
                if sub_node.type in {"identifier", "field_identifier"}:
                    function_name = source_code[sub_node.start_byte : sub_node.end_byte]
                    break

            if function_name == "":
                continue

            # Initialize the raw data of a function
            start_line_number = source_code[: function_node.start_byte].count("\n") + 1
            end_line_number = source_code[: function_node.end_byte].count("\n") + 1
            function_id = len(self.functionRawDataDic) + 1

            self.functionRawDataDic[function_id] = (
                function_name,
                start_line_number,
                end_line_number,
                function_node,
            )
            self.functionToFile[function_id] = file_path

            if function_name not in self.functionNameToId:
                self.functionNameToId[function_name] = set([])
            self.functionNameToId[function_name].add(function_id)
        return

    def parse_global_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """
        Parse the global macro information in a source file.
        :param file_path: The path of the source file.
        :param source_code: The content of the source file.
        :param tree: The parse tree of the source file.
        """
        # TODO. Implement the function to parse macro information and other global info
        return


class Go_TSAnalyzer(TSAnalyzer):
    """
    TSAnalyzer class for retrieving necessary facts or functions for llmtools
    """

    def create_ts_parser(self):
        return Go_TSParser(self.code_in_projects, self.language)

    #################################################
    ########## Call Graph Analysis ##################
    #################################################
    def extract_call_graph_edges(self, current_function: Function) -> None:
        """
        Extract the call graph edges.
        :param current_function: the function to be analyzed
        """
        # Over-approximate the caller-callee relationship via function names, achieved by get_callee_at_callsite
        file_name = self.ts_parser.functionToFile[current_function.function_id]
        file_content = self.ts_parser.fileContentDic[file_name]

        function_call_node_type = "call_expression"
        all_call_sites = find_nodes_by_type(
            current_function.parse_tree_root_node, function_call_node_type
        )
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

    def get_callee_name_at_call_site(
        self, node: tree_sitter.Node, source_code: str
    ) -> str:
        """
        Get the callee name at the call site.
        :param node: the node of the call site
        :param source_code: the content of the file
        :return: the callee name
        """
        assert node.type == "call_expression"
        for sub_node in node.children:
            if sub_node.type == "selector_expression":
                for sub_sub_node in sub_node.children:
                    if sub_sub_node.type == "field_identifier":
                        return source_code[
                            sub_sub_node.start_byte : sub_sub_node.end_byte
                        ]
            sub_node_types = [sub_node.type for sub_node in node.children]
            if "selector_expression" not in sub_node_types:
                for sub_node in node.children:
                    if sub_node.type == "identifier":
                        return source_code[sub_node.start_byte : sub_node.end_byte]
        return ""

    def get_callsite_by_callee_name(
        self, current_function: Function, callee_name: str
    ) -> List[tree_sitter.Node]:
        """
        Find the call sites by the callee function name.
        :param current_function: the function to be analyzed
        :param callee_name: the callee function name
        :return: the call sites
        """
        results = []
        file_content = self.code_in_projects[current_function.file_name]
        call_site_nodes = find_nodes_by_type(
            current_function.parse_tree_root_node, "call_expression"
        )
        for call_site in call_site_nodes:
            if (
                self.get_callee_name_at_call_site(call_site, file_content)
                == callee_name
            ):
                results.append(call_site)
                break
        return results

    def get_arguments_at_callsite(
        self, node: tree_sitter.Node, source_code: str
    ) -> List[str]:
        """
        Get arguments at the call site.
        :param node: the node of the call site
        :param source_code: the content of the file
        :return: the names of the arguments
        """
        arguments = []
        for sub_node in node.children:
            if sub_node.type == "argument_list":
                arg_list = sub_node.children[1:-1]
                for element in arg_list:
                    if element.type != ",":
                        arguments.append(
                            source_code[element.start_byte : element.end_byte]
                        )
        return arguments

    #################################################
    ########## AST Node Type Analysis ###############
    #################################################

    def get_paras_in_single_function(
        self, current_function: Function
    ) -> Set[Tuple[str, int, int]]:
        """
        Find the parameters of the function.
        :param current_function: the function to be analyzed
        :return: (para_name, line_number, index) of the parameters
        """
        file_content = self.code_in_projects[current_function.file_name]
        paras = set([])
        parameter_list_nodes = []
        for sub_node in current_function.parse_tree_root_node.children:
            if sub_node.type in "parameter_list":
                parameter_list_nodes.append(sub_node)

        index = 0
        for parameter_list_node in parameter_list_nodes:
            for sub_node in parameter_list_node.children:
                if sub_node.type in "parameter_declaration":
                    for sub_sub_node in sub_node.children:
                        if sub_sub_node.type in "identifier":
                            parameter_name = file_content[
                                sub_sub_node.start_byte : sub_sub_node.end_byte
                            ]
                            line_number = (
                                file_content[: sub_sub_node.start_byte].count("\n") + 1
                            )
                            paras.add((parameter_name, line_number, index))
                            index += 1
                            break
        return paras

    def get_args_by_callee_name(
        self, current_function: Function, callee: str
    ) -> Set[Tuple[str, int, int]]:
        """
        Find the arguments of the callee function.
        :param current_function: the function to be analyzed
        :param callee: the callee function name
        :return: (arg_name, line_number, index) of the arguments
        """
        args = set([])
        file_content = self.code_in_projects[current_function.file_name]
        call_site_nodes = find_nodes_by_type(
            current_function.parse_tree_root_node, "call_expression"
        )
        for call_site in call_site_nodes:
            actual_callee = self.get_callee_name_at_call_site(call_site, file_content)
            if actual_callee != callee:
                continue
            for child in call_site.children:
                if child.type == "argument_list":
                    arg_list = child.children[1:-1]
                    index = 0
                    for element in arg_list:
                        if element.type != ",":
                            line_number = (
                                file_content[: element.start_byte].count("\n") + 1
                            )
                            arg_name = file_content[
                                element.start_byte : element.end_byte
                            ]
                            args.add((arg_name, line_number, index))
                            index += 1
        return args

    def get_retstmts_in_single_function(
        self, current_function: Function
    ) -> List[Tuple[str, int]]:
        """
        Find the return statements in the function.
        :param current_function: the function to be analyzed
        :return: (ret_stmt, line_number) of the return statements
        """
        retstmts = []
        file_content = self.code_in_projects[current_function.file_name]
        retnodes = find_nodes_by_type(
            current_function.parse_tree_root_node, "return_statement"
        )
        for retnode in retnodes:
            line_number = file_content[: retnode.start_byte].count("\n") + 1
            retstmts.append(
                (file_content[retnode.start_byte : retnode.end_byte], line_number)
            )
        return retstmts

    #################################################
    ########## Control Flow Analysis ################
    #################################################

    def get_if_statements(
        self, function: Function, source_code: str
    ) -> Dict[Tuple, Tuple]:
        """
        Find the if statements in the Go functions.
        :param function: the function to be analyzed
        :param source_code: the content of the file
        :return: a dictionary containing the if statement info and the line number: `(start_line, end_line): info`
        """
        if_statement_nodes = find_nodes_by_type(
            function.parse_tree_root_node, "if_statement"
        )
        if_statements = {}

        for if_statement_node in if_statement_nodes:
            condition_str = ""
            condition_start_line = 0
            condition_end_line = 0
            true_branch_start_line = 0
            true_branch_end_line = 0
            else_branch_start_line = 0
            else_branch_end_line = 0

            # store the types of sub_nodes of if_statement_node in a list
            sub_node_types = [sub_node.type for sub_node in if_statement_node.children]
            block_index = sub_node_types.index("block")
            true_branch_start_line = (
                source_code[: if_statement_node.children[block_index].start_byte].count(
                    "\n"
                )
                + 1
            )
            true_branch_end_line = (
                source_code[: if_statement_node.children[block_index].end_byte].count(
                    "\n"
                )
                + 1
            )

            if "else" in sub_node_types:
                else_index = sub_node_types.index("else")
                else_branch_start_line = (
                    source_code[
                        : if_statement_node.children[else_index + 1].start_byte
                    ].count("\n")
                    + 1
                )
                else_branch_end_line = (
                    source_code[
                        : if_statement_node.children[else_index + 1].end_byte
                    ].count("\n")
                    + 1
                )
            else:
                else_branch_start_line = 0
                else_branch_end_line = 0
            condition_start_line = (
                source_code[
                    : if_statement_node.children[block_index - 1].start_byte
                ].count("\n")
                + 1
            )
            condition_end_line = (
                source_code[
                    : if_statement_node.children[block_index - 1].end_byte
                ].count("\n")
                + 1
            )
            condition_str = source_code[
                if_statement_node.children[block_index - 1]
                .start_byte : if_statement_node.children[block_index - 1]
                .end_byte
            ]

            if_statement_start_line = (
                source_code[: if_statement_node.start_byte].count("\n") + 1
            )
            if_statement_end_line = (
                source_code[: if_statement_node.end_byte].count("\n") + 1
            )
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

    def get_loop_statements(
        self, function: Function, source_code: str
    ) -> Dict[Tuple, Tuple]:
        """
        Find the loop statements in the Go functions.
        :param function: the function to be analyzed
        :param source_code: the content of the file
        :return: a dictionary containing the if statement info and the line number: `(start_line, end_line): info`
        """
        loop_statements = {}
        for_statement_nodes = find_nodes_by_type(
            function.parse_tree_root_node, "for_statement"
        )

        for loop_node in for_statement_nodes:
            loop_start_line = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end_line = source_code[: loop_node.end_byte].count("\n") + 1

            header_line_start = 0
            header_line_end = 0
            header_str = ""
            loop_body_start_line = 0
            loop_body_end_line = 0

            if len(loop_node.children) == 3:
                loop_body_start_line = (
                    source_code[: loop_node.children[2].start_byte].count("\n") + 1
                )
                loop_body_end_line = (
                    source_code[: loop_node.children[2].end_byte].count("\n") + 1
                )
                header_line_start = (
                    source_code[: loop_node.children[1].start_byte].count("\n") + 1
                )
                header_line_end = (
                    source_code[: loop_node.children[1].end_byte].count("\n") + 1
                )
                header_str = source_code[
                    loop_node.children[1].start_byte : loop_node.children[1].end_byte
                ]
            else:
                loop_body_start_line = (
                    source_code[: loop_node.children[1].start_byte].count("\n") + 1
                )
                loop_body_end_line = (
                    source_code[: loop_node.children[1].end_byte].count("\n") + 1
                )
                header_line_start = loop_start_line
                header_line_end = loop_start_line
                header_str = ""

            loop_statements[(loop_start_line, loop_end_line)] = (
                header_line_start,
                header_line_end,
                header_str,
                loop_body_start_line,
                loop_body_end_line,
            )
        return loop_statements
