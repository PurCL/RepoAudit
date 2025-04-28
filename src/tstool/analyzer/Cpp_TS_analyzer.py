import sys
from os import path
from typing import List, Tuple, Dict, Set
import tree_sitter

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

from .TS_analyzer import *
from memory.syntactic.function import *
from memory.syntactic.value import *


class Cpp_TSAnalyzer(TSAnalyzer):
    """
    TSAnalyzer for C/C++ source files using tree-sitter.
    Implements language-specific parsing and analysis.
    """

    def extract_function_info(
        self, file_path: str, source_code: str, tree: tree_sitter.Tree
    ) -> None:
        """
        Parse the function information in a source file.
        """
        for function_definition_node in find_nodes_by_type(
            tree.root_node, "function_definition"
        ):
            for function_declaration_node in find_nodes_by_type(
                function_definition_node, "function_declarator"
            ):
                function_name = ""
                for sub_node in function_declaration_node.children:
                    if sub_node.type in {"identifier", "field_identifier"}:
                        function_name = source_code[
                            sub_node.start_byte : sub_node.end_byte
                        ]
                        break
                    elif sub_node.type == "qualified_identifier":
                        qualified_function_name = source_code[
                            sub_node.start_byte : sub_node.end_byte
                        ]
                        function_name = qualified_function_name.split("::")[-1]
                        break
                if function_name == "":
                    continue

                # Initialize the raw data of a function
                start_line_number = (
                    source_code[: function_definition_node.start_byte].count("\n") + 1
                )
                end_line_number = (
                    source_code[: function_definition_node.end_byte].count("\n") + 1
                )
                function_id = len(self.functionRawDataDic) + 1

                self.functionRawDataDic[function_id] = (
                    function_name,
                    start_line_number,
                    end_line_number,
                    function_definition_node,
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
        Parse the global macro information in a source file.
        """
        all_macro_nodes = find_nodes_by_type(tree.root_node, "preproc_def")
        for node in all_macro_nodes:
            macro_name = ""
            macro_definition = ""
            for child in node.children:
                if child.type == "identifier":
                    macro_name = source_code[child.start_byte : child.end_byte]
                if child.type == "preproc_arg":
                    macro_definition = source_code[child.start_byte : child.end_byte]
            if macro_name != "" and macro_definition != "":
                self.glb_var_map[macro_name] = macro_definition

        all_macro_nodes = find_nodes_by_type(tree.root_node, "preproc_function_def")
        for node in all_macro_nodes:
            function_name = ""
            for child in node.children:
                if child.type == "identifier":
                    function_name = source_code[child.start_byte : child.end_byte]
                if child.type == "preproc_params":
                    function_name += source_code[child.start_byte : child.end_byte]
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
                self.functionNameToId[function_name] = set()
            self.functionNameToId[function_name].add(function_id)
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
        sub_sub_nodes = []
        for sub_node in node.children:
            if sub_node.type == "identifier":
                sub_sub_nodes.append(sub_node)
            else:
                for sub_sub_node in sub_node.children:
                    sub_sub_nodes.append(sub_sub_node)
            break
        sub_sub_node_types = [
            source_code[sub_sub_node.start_byte : sub_sub_node.end_byte]
            for sub_sub_node in sub_sub_nodes
        ]
        if len(sub_sub_node_types) == 0:
            return ""
        index_of_last_dot = (
            len(sub_sub_node_types) - 1 - sub_sub_node_types[::-1].index(".")
            if "." in sub_sub_node_types
            else -1
        )
        index_of_last_arrow = (
            len(sub_sub_node_types) - 1 - sub_sub_node_types[::-1].index("->")
            if "->" in sub_sub_node_types
            else -1
        )
        function_name = sub_sub_node_types[
            max(index_of_last_dot, index_of_last_arrow) + 1
        ]
        return function_name

    def get_callsites_by_callee_name(
        self, current_function: Function, callee_name: str
    ) -> List[tree_sitter.Node]:
        """
        Find the call sites by the callee function name.
        :param current_function: the function to be analyzed
        :param callee_name: the callee function name
        :return: the call site nodes
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
        parameters = find_nodes_by_type(
            current_function.parse_tree_root_node, "parameter_declaration"
        )
        index = 0
        for parameter_node in parameters:
            for sub_node in find_nodes_by_type(parameter_node, "identifier"):
                parameter_name = file_content[sub_node.start_byte : sub_node.end_byte]
                line_number = file_content[: sub_node.start_byte].count("\n") + 1
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
        Find the return values of a function.
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
        Identify if-statements in the function.
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

            for child in if_node.children:
                if child.type in ["parenthesized_expression", "condition_clause"]:
                    condition_start_line = (
                        source_code[: child.start_byte].count("\n") + 1
                    )
                    condition_end_line = source_code[: child.end_byte].count("\n") + 1
                    condition_str = source_code[child.start_byte : child.end_byte]
                if "statement" in child.type:
                    true_branch_start_line = (
                        source_code[: child.start_byte].count("\n") + 1
                    )
                    true_branch_end_line = source_code[: child.end_byte].count("\n") + 1
                if child.type == "else_clause":
                    else_branch_start_line = (
                        source_code[: child.start_byte].count("\n") + 1
                    )
                    else_branch_end_line = source_code[: child.end_byte].count("\n") + 1

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
        Identify loop statements in the function.
        """
        loop_statements = {}
        root_node = function.parse_tree_root_node
        for_statement_nodes = find_nodes_by_type(root_node, "for_statement")
        while_statement_nodes = find_nodes_by_type(root_node, "while_statement")

        for loop_node in for_statement_nodes:
            loop_start_line = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end_line = source_code[: loop_node.end_byte].count("\n") + 1

            header_line_start = 0
            header_line_end = 0
            header_str = ""
            loop_body_start_line = 0
            loop_body_end_line = 0
            header_start_byte = 0
            header_end_byte = 0

            for child in loop_node.children:
                if child.type == "(":
                    header_line_start = source_code[: child.start_byte].count("\n") + 1
                    header_start_byte = child.end_byte
                if child.type == ")":
                    header_line_end = source_code[: child.end_byte].count("\n") + 1
                    header_end_byte = child.start_byte
                    header_str = source_code[header_start_byte:header_end_byte]
                if child.type == "block":
                    lower_lines = []
                    upper_lines = []
                    for sub in child.children:
                        if sub.type not in {"{", "}"}:
                            lower_lines.append(
                                source_code[: sub.start_byte].count("\n") + 1
                            )
                            upper_lines.append(
                                source_code[: sub.end_byte].count("\n") + 1
                            )
                    if lower_lines and upper_lines:
                        loop_body_start_line = min(lower_lines)
                        loop_body_end_line = max(upper_lines)
                    else:
                        loop_body_start_line = header_line_end
                        loop_body_end_line = header_line_end
                if "statement" in child.type:
                    loop_body_start_line = (
                        source_code[: child.start_byte].count("\n") + 1
                    )
                    loop_body_end_line = source_code[: child.end_byte].count("\n") + 1
            loop_statements[(loop_start_line, loop_end_line)] = (
                header_line_start,
                header_line_end,
                header_str,
                loop_body_start_line,
                loop_body_end_line,
            )

        for loop_node in while_statement_nodes:
            loop_start_line = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end_line = source_code[: loop_node.end_byte].count("\n") + 1

            header_line_start = 0
            header_line_end = 0
            header_str = ""
            loop_body_start_line = 0
            loop_body_end_line = 0

            for child in loop_node.children:
                if child.type == "parenthesized_expression":
                    header_line_start = source_code[: child.start_byte].count("\n") + 1
                    header_line_end = source_code[: child.end_byte].count("\n") + 1
                    header_str = source_code[child.start_byte : child.end_byte]
                if "statement" in child.type:
                    lower_lines = []
                    upper_lines = []
                    for sub in child.children:
                        if sub.type not in {"{", "}"}:
                            lower_lines.append(
                                source_code[: sub.start_byte].count("\n") + 1
                            )
                            upper_lines.append(
                                source_code[: sub.end_byte].count("\n") + 1
                            )
                    if lower_lines and upper_lines:
                        loop_body_start_line = min(lower_lines)
                        loop_body_end_line = max(upper_lines)
                    else:
                        loop_body_start_line = header_line_end
                        loop_body_end_line = header_line_end
            loop_statements[(loop_start_line, loop_end_line)] = (
                header_line_start,
                header_line_end,
                header_str,
                loop_body_start_line,
                loop_body_end_line,
            )
        return loop_statements
