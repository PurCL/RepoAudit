import sys
from os import path
from typing import List, Tuple, Dict, Set
import tree_sitter

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

from .TS_analyzer import *
from memory.syntactic.function import *
from memory.syntactic.value import *


class Go_TSAnalyzer(TSAnalyzer):
    """
    TSAnalyzer for Go source files using tree-sitter.
    Implements Go-specific parsing and analysis.
    """

    def extract_function_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """
        Parse the function information in a source file.
        :param file_path: The path of the source file.
        :param source_code: The content of the source file.
        :param tree: The parse tree of the source file.
        """
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

    def extract_global_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """
        Parse global (macro) information in a Go source file.
        Currently not implemented.
        """
        # TODO: Implement parsing of global information if necessary.
        return

    def get_callee_name_at_call_site(
        self, node: tree_sitter.Node, source_code: str
    ) -> str:
        """
        Get the callee name at the call site.
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

    def get_callsites_by_callee_name(
        self, current_function: Function, callee_name: str
    ) -> List[tree_sitter.Node]:
        """
        Find the call site nodes by the callee name.
        """
        results = []
        file_content = self.code_in_files[current_function.file_path]
        call_site_nodes = find_nodes_by_type(
            current_function.parse_tree_root_node, "call_expression"
        )
        for call_site in call_site_nodes:
            if (
                self.get_callee_name_at_call_site(call_site, file_content)
                == callee_name
            ):
                results.append(call_site)
        return results

    def get_arguments_at_callsite(
        self, current_function: Function, call_site_node: tree_sitter.Node
    ) -> Set[Value]:
        """
        Get arguments from a call site in a function.
        :param current_function: the function to be analyzed
        :param call_site_node: the node of the call site
        :return: the arguments
        """
        arguments = set([])
        file_name = current_function.file_path
        source_code = self.code_in_files[file_name]
        for sub_node in call_site_node.children:
            if sub_node.type == "argument_list":
                arg_list = sub_node.children[1:-1]
                for element in arg_list:
                    if element.type != ",":
                        line_number = source_code[: element.start_byte].count("\n") + 1
                        arguments.add(
                            Value(
                                source_code[element.start_byte : element.end_byte],
                                line_number,
                                ValueLabel.ARG,
                                file_name,
                                len(arguments),
                            )
                        )
        return arguments

    def get_parameters_in_single_function(
        self, current_function: Function
    ) -> Set[Value]:
        """
        Find the parameters of a function.
        :param current_function: The function to be analyzed.
        :return: A set of parameters as values
        """
        if current_function.paras is not None:
            return current_function.paras
        current_function.paras = set([])
        file_content = self.code_in_files[current_function.file_path]
        parameter_list_nodes = []
        for sub_node in current_function.parse_tree_root_node.children:
            if sub_node.type in "parameter_list":
                parameter_list_nodes.append(sub_node)

        index = 0
        parameter_list_node = parameter_list_nodes[-1]
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
                        current_function.paras.add(
                            Value(
                                parameter_name,
                                line_number,
                                ValueLabel.PARA,
                                current_function.file_path,
                                index,
                            )
                        )
                        break
                index += 1
        return current_function.paras

    def get_return_values_in_single_function(
        self, current_function: Function
    ) -> Set[Value]:
        """
        Find the return values of a Go function
        :param current_function: The function to be analyzed.
        :return: A set of return values
        """
        if current_function.retvals is not None:
            return current_function.retvals

        current_function.retvals = set([])
        file_content = self.code_in_files[current_function.file_path]
        retnodes = find_nodes_by_type(
            current_function.parse_tree_root_node, "return_statement"
        )
        for retnode in retnodes:
            line_number = file_content[: retnode.start_byte].count("\n") + 1
            sub_node_types = [sub_node.type for sub_node in retnode.children]
            index = 0
            if "expression_list" in sub_node_types:
                expression_list_index = sub_node_types.index("expression_list")
                for expression_node in retnode.children[expression_list_index].children:
                    if expression_node.type != ",":
                        current_function.retvals.add(
                            Value(
                                file_content[
                                    expression_node.start_byte : expression_node.end_byte
                                ],
                                line_number,
                                ValueLabel.RET,
                                current_function.file_path,
                                index,
                            )
                        )
                        index += 1
            else:
                current_function.retvals.add(
                    Value(
                        "nil",
                        line_number,
                        ValueLabel.RET,
                        current_function.file_path,
                        0,
                    )
                )
        return current_function.retvals

    def get_if_statements(
        self, function: Function, source_code: str
    ) -> Dict[Tuple, Tuple]:
        """
        Find if-statements in the Go function.
        Assume the structure: condition, block and optional else clause.
        """
        if_statement_nodes = find_nodes_by_type(
            function.parse_tree_root_node, "if_statement"
        )
        if_statements = {}
        for if_node in if_statement_nodes:
            sub_node_types = [sub.type for sub in if_node.children]
            try:
                block_index = sub_node_types.index("block")
            except ValueError:
                continue

            true_branch_start_line = (
                source_code[: if_node.children[block_index].start_byte].count("\n") + 1
            )
            true_branch_end_line = (
                source_code[: if_node.children[block_index].end_byte].count("\n") + 1
            )

            if "else" in sub_node_types:
                else_index = sub_node_types.index("else")
                else_branch_start_line = (
                    source_code[: if_node.children[else_index + 1].start_byte].count(
                        "\n"
                    )
                    + 1
                )
                else_branch_end_line = (
                    source_code[: if_node.children[else_index + 1].end_byte].count("\n")
                    + 1
                )
            else:
                else_branch_start_line = 0
                else_branch_end_line = 0

            condition_index = block_index - 1
            condition_start_line = (
                source_code[: if_node.children[condition_index].start_byte].count("\n")
                + 1
            )
            condition_end_line = (
                source_code[: if_node.children[condition_index].end_byte].count("\n")
                + 1
            )
            condition_str = source_code[
                if_node.children[condition_index]
                .start_byte : if_node.children[condition_index]
                .end_byte
            ]

            if_statement_start_line = source_code[: if_node.start_byte].count("\n") + 1
            if_statement_end_line = source_code[: if_node.end_byte].count("\n") + 1
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
        Find loop statements in the Go function.
        """
        loop_statements = {}
        for_node_list = find_nodes_by_type(
            function.parse_tree_root_node, "for_statement"
        )
        for loop_node in for_node_list:
            loop_start_line = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end_line = source_code[: loop_node.end_byte].count("\n") + 1

            header_line_start = 0
            header_line_end = 0
            header_str = ""
            loop_body_start_line = 0
            loop_body_end_line = 0
            if len(loop_node.children) >= 3:
                header_line_start = (
                    source_code[: loop_node.children[1].start_byte].count("\n") + 1
                )
                header_line_end = (
                    source_code[: loop_node.children[1].end_byte].count("\n") + 1
                )
                header_str = source_code[
                    loop_node.children[1].start_byte : loop_node.children[1].end_byte
                ]
                loop_body_start_line = (
                    source_code[: loop_node.children[2].start_byte].count("\n") + 1
                )
                loop_body_end_line = (
                    source_code[: loop_node.children[2].end_byte].count("\n") + 1
                )
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
