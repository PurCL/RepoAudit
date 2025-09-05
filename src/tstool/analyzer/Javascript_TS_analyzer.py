import sys
from os import path
from typing import List, Tuple, Dict, Set
import tree_sitter

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

from .TS_analyzer import *
from memory.syntactic.function import *
from memory.syntactic.value import *


class Javascript_TSAnalyzer(TSAnalyzer):
    """
    TSAnalyzer for Javascript source files using tree-sitter.
    Implements Javascript-specific parsing and analysis.
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
        all_function_header_nodes = find_nodes_by_type(
            tree.root_node, "function_declaration"
        )
        all_variable_declarator_nodes = find_nodes_by_type(
            tree.root_node, "variable_declarator"
        )
        
        for node in all_function_header_nodes:
            function_name = ""
            for sub_node in node.children:
                if sub_node.type == "identifier":
                    function_name = source_code[sub_node.start_byte : sub_node.end_byte]
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
                node,
            )
            self.functionToFile[function_id] = file_path

            if function_name not in self.functionNameToId:
                self.functionNameToId[function_name] = set([])
            self.functionNameToId[function_name].add(function_id)
            
        for node in all_variable_declarator_nodes:
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")

            if not name_node or not value_node:
                continue

            if value_node.type != "arrow_function" and value_node.type != "function_expression":
                continue
            
            function_name = source_code[name_node.start_byte : name_node.end_byte]
            start_line = source_code[:node.start_byte].count("\n") + 1
            end_line = source_code[:node.end_byte].count("\n") + 1
            function_id = len(self.functionRawDataDic) + 1

            self.functionRawDataDic[function_id] = (
                function_name, start_line, end_line, node
            )
            self.functionToFile[function_id] = file_path
            self.functionNameToId.setdefault(function_name, set()).add(function_id)
        
        return

    def extract_global_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """
        Parse global variable information from a Javascript source file.
        For Javascript, this may include module-level variables.
        Currently not implemented.
        """
        # TODO: Add global variable analysis if needed.
        return

    def get_callee_name_at_call_site(
        self, node: tree_sitter.Node, source_code: str
    ) -> str:
        """
        Get the callee name at the call site.
        :param node: the node of the call site
        :param source_code: the content of the file
        """
        function_name = ""
        for sub_node in node.children:
            if sub_node.type == "identifier":
                function_name = source_code[sub_node.start_byte : sub_node.end_byte]
                break
            if sub_node.type == "member_expression":
                for sub_sub_node in sub_node.children:
                    if sub_sub_node.type == "identifier":
                        function_name = source_code[
                            sub_sub_node.start_byte : sub_sub_node.end_byte
                        ]
                break
        return function_name

    def get_callsites_by_callee_name(
        self, current_function: Function, callee_name: str
    ) -> List[tree_sitter.Node]:
        """
        Find the call sites by the callee function name.
        :param current_function: the function to be analyzed
        :param callee_name: the callee function name
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
        arguments: Set[Value] = set([])
        file_name = current_function.file_path
        source_code = self.code_in_files[file_name]
        for sub_node in call_site_node.children:
            if sub_node.type == "arguments":
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
        parameters = find_nodes_by_type(
            current_function.parse_tree_root_node, "formal_parameters"
        )

        index = 0
        for parameter_node in parameters:
            parameter_name = ""
            for sub_node in parameter_node.children:
                for sub_sub_node in find_nodes_by_type(sub_node, "identifier"):
                    parameter_name = file_content[
                        sub_sub_node.start_byte : sub_sub_node.end_byte
                    ]
                    if parameter_name != "" and parameter_name != "self":
                        line_number = (
                            file_content[: sub_node.start_byte].count("\n") + 1
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
            restmts_str = file_content[retnode.start_byte : retnode.end_byte]
            returned_value = restmts_str.replace("return", "").strip()
            current_function.retvals.add(
                Value(
                    returned_value,
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
        Identify if-statements in the Javascript function.
        This is a simplified analysis for illustrative purposes.
        """
        if_statement_nodes = find_nodes_by_type(
            function.parse_tree_root_node, "if_statement"
        )
        if_statements = {}
        for if_node in if_statement_nodes:
            condition_str = ""
            condition_start_line = 0
            condition_end_line = 0
            true_branch_start_line = 0
            true_branch_end_line = 0
            else_branch_start_line = 0
            else_branch_end_line = 0

            block_num = 0
            for sub_target in if_node.children:
                if sub_target.type == "parenthesized_expression":
                    condition_start_line = (
                        source_code[: sub_target.start_byte].count("\n") + 1
                    )
                    condition_end_line = (
                        source_code[: sub_target.end_byte].count("\n") + 1
                    )
                    condition_str = source_code[
                        sub_target.start_byte : sub_target.end_byte
                    ]
                if sub_target.type == "statement_block":
                    lower_lines = []
                    upper_lines = []
                    for sub_sub in sub_target.children:
                        if sub_sub.type not in {"{", "}"}:
                            lower_lines.append(
                                source_code[: sub_sub.start_byte].count("\n") + 1
                            )
                            upper_lines.append(
                                source_code[: sub_sub.end_byte].count("\n") + 1
                            )
                    if lower_lines and upper_lines:
                        if block_num == 0:
                            true_branch_start_line = min(lower_lines)
                            true_branch_end_line = max(upper_lines)
                            block_num += 1
                        elif block_num == 1:
                            else_branch_start_line = min(lower_lines)
                            else_branch_end_line = max(upper_lines)
                            block_num += 1
                if sub_target.type == "expression_statement":
                    true_branch_start_line = (
                        source_code[: sub_target.start_byte].count("\n") + 1
                    )
                    true_branch_end_line = (
                        source_code[: sub_target.end_byte].count("\n") + 1
                    )

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
        Identify loop statements (for and while) in the Javascript function.
        """
        loops = {}
        loop_nodes = find_nodes_by_type(function.parse_tree_root_node, "for_statement")
        loop_nodes.extend(
            find_nodes_by_type(function.parse_tree_root_node, "for_in_statement")
        )
        loop_nodes.extend(
            find_nodes_by_type(function.parse_tree_root_node, "while_statement")
        )
        for node in loop_nodes:
            start_line = source_code[: node.start_byte].count("\n") + 1
            end_line = source_code[: node.end_byte].count("\n") + 1
            # Simplified header and body analysis.
            loops[(start_line, end_line)] = (
                start_line,
                start_line,
                "",
                start_line,
                end_line,
            )
        return loops
