import sys
from os import path
from typing import List, Optional, Tuple, Dict, Set
from tree_sitter import Node, Tree

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

from .TS_analyzer import *
from memory.syntactic.function import *
from memory.syntactic.value import *


class Go_TSAnalyzer(TSAnalyzer):
    """
    TSAnalyzer for Go source files using tree-sitter.
    Implements Go-specific parsing and analysis.
    """

    def __init__(
        self,
        code_in_files: Dict[str, str],
        language_name: str,
        max_symbolic_workers_num=10,
    ) -> None:
        """
        Initialize the Go_TSAnalyzer.
        :param code_in_files: A dictionary mapping file paths to their content.
        :param language_name: The name of the programming language (e.g., "Go").
        :param max_symbolic_workers_num: The maximum number of symbolic workers.
        """
        # We need to consider packages imported by each source file:
        #     <file_path> -> <package_name> -> <package_path>
        # For example:
        #     /path/to/file.go -> "fmt" -> "fmt" (import "fmt")
        #     /path/to/file.go -> "mypackage" -> "myapp/mypackage" (import "myapp/mypackage")
        #     /path/to/file.go -> "m" -> "myapp/mypackage" (import m "myapp/mypackage")
        self.imported_packages: Dict[str, Dict[str, str]] = {}

        super().__init__(code_in_files, language_name, max_symbolic_workers_num)

    def extract_function_info(
        self, file_path: str, source_code: str, tree: Tree
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

    def extract_global_info(self, file_path: str, source_code: str, tree: Tree) -> None:
        """
        Parse global (macro) information in a Go source file.
        Currently not implemented.
        """

        if file_path not in self.imported_packages:
            self.imported_packages[file_path] = {}

        # Parsing imports in Go
        all_import_specs = find_nodes_by_type(tree.root_node, "import_spec")
        for import_spec in all_import_specs:
            package_paths = find_nodes_by_type(
                import_spec, "interpreted_string_literal"
            )
            assert len(package_paths) == 1
            package_path = source_code[
                package_paths[0].start_byte : package_paths[0].end_byte
            ][1:-1]

            package_identifiers = find_nodes_by_type(import_spec, "package_identifier")
            assert 0 <= len(package_identifiers) <= 1

            if len(package_identifiers) == 1:
                package_identifier = source_code[
                    package_identifiers[0].start_byte : package_identifiers[0].end_byte
                ]
                self.imported_packages[file_path][package_identifier] = package_path
            else:
                # If no package identifier is found, use the package path as the key.
                package_identifier = package_path.split("/")[-1]
                self.imported_packages[file_path][package_identifier] = package_path

        return

    def get_callee_name_at_call_site(self, node: Node, source_code: str) -> str:
        """
        Get the callee name at the call site.
        """
        assert (
            node.type == "call_expression"
        ), f"Expected a call_expression node, but got {node.type}."

        # XXX(ZZ): Go have many different syntaxes for function calls. Here, we only
        # consider the most common ones: function calls and method calls.
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

        # If no identifier is found, return an empty string. This could happen
        # if the call site is not a function call or method call.
        return ""

    def get_callsites_by_callee_name(
        self, current_function: Function, callee_name: str
    ) -> List[Node]:
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

    def get_receiver_arguments_at_callsite(
        self, current_function: Function, call_site_node: Node
    ) -> Optional[Value]:
        assert (
            call_site_node.type == "call_expression"
        ), f"Expected a call_expression node, but got {call_site_node.type}."

        method_node = call_site_node.children[0]
        if method_node.type == "identifier":
            # This is a normal function call.
            return None

        assert (
            method_node.type == "selector_expression"
        ), f"Expected a selector_expression node, but got {call_site_node.children[0].type}."

        file_name = current_function.file_path
        source_code = self.code_in_files[file_name]

        receiver_node = method_node.children[0]
        assert (
            receiver_node.type == "identifier"
            or receiver_node.type == "selector_expression"
        ), f"Expected an identifier or selector_expression node, but got {receiver_node.type}."

        first_identifier = receiver_node
        while first_identifier.type == "selector_expression":
            first_identifier = first_identifier.children[0]
        assert (
            first_identifier.type == "identifier"
        ), f"Expected an identifier node, but got {first_identifier.type}."

        first_identifier_name = source_code[
            first_identifier.start_byte : first_identifier.end_byte
        ]

        # TODO (ZZ): Name collisions are not handled—e.g., reusing an identifier for a variable within the same scope.
        if first_identifier_name in self.imported_packages[file_name]:
            # This is an imported method.
            return None

        receiver_name = source_code[receiver_node.start_byte : receiver_node.end_byte]
        line_number = source_code[: receiver_node.start_byte].count("\n") + 1
        return Value(
            receiver_name,
            line_number,
            ValueLabel.OBJ_ARG,
            file_name,
            -1,
        )

    def get_arguments_at_callsite(
        self, current_function: Function, call_site_node: Node
    ) -> Set[Value]:
        """
        Get arguments from a call site in a function.
        :param current_function: the function to be analyzed
        :param call_site_node: the node of the call site
        :return: the arguments
        """
        assert (
            call_site_node.type == "call_expression"
        ), f"Expected a call_expression node, but got {call_site_node.type}."

        arguments: Set[Value] = set()
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

    def analyze_parameters_in_single_function(self, current_function: Function) -> None:
        """
        Find the parameters of a function.
        :param current_function: The function to be analyzed.
        :return: A set of parameters as values
        """
        if current_function._paras is not None:
            return
        current_function._paras = set()

        file_content = self.code_in_files[current_function.file_path]

        # There are a lot of different syntaxes for function declarations in Go.
        #   - func gee(x int)
        #   - func foo(x int) (y int)
        #   - func (A *Data) haa(x int)
        #   - func (A *Data) kuu(x int) (y int)
        root_node = current_function.parse_tree_root_node
        assert (
            root_node.children[0].type == "func"
        ), f"The first child of the root node should be 'func', but got {root_node.children[0].type}."

        # XXX (ZZ): There are some shaky parts I observed in the Go parser, which might
        # change if the codebased of Tree-sitter is updated.
        parameter_list_nodes: List[Tuple[Node, bool]] = []
        if root_node.children[1].type == "parameter_list":
            # This will be the case for a method for a struct.
            #   - func (A *Data) haa(x int)
            assert (
                root_node.children[2].type == "field_identifier"
            ), f"The third child of the root node should be 'field_identifier', but got {root_node.children[2].type}."
            parameter_list_nodes.append((root_node.children[1], True))

            assert (
                root_node.children[3].type == "parameter_list"
            ), f"The fourth child of the root node should be 'parameter_list', but got {root_node.children[3].type}."
            parameter_list_nodes.append((root_node.children[3], False))
        else:
            # This will be the case for a normal function.
            #   - func gee(x int)
            assert (
                root_node.children[1].type == "identifier"
            ), f"The second child of the root node should be 'identifier', but got {root_node.children[1].type}."

            assert (
                root_node.children[2].type == "parameter_list"
            ), f"The third child of the root node should be 'parameter_list', but got {root_node.children[2].type}."
            parameter_list_nodes.append((root_node.children[2], False))

        index = 0
        for parameter_list_node, is_receiver in parameter_list_nodes:
            assert (
                parameter_list_node.type == "parameter_list"
            ), f"The parameter list node should be 'parameter_list', but got {parameter_list_node.type}."

            for sub_node in parameter_list_node.children:
                if sub_node.type in [
                    "parameter_declaration",
                    "variadic_parameter_declaration",
                ]:
                    for sub_sub_node in sub_node.children:
                        if sub_sub_node.type == "identifier":
                            parameter_name = file_content[
                                sub_sub_node.start_byte : sub_sub_node.end_byte
                            ]
                            line_number = (
                                file_content[: sub_sub_node.start_byte].count("\n") + 1
                            )

                            if is_receiver:
                                assert sub_node.type == "parameter_declaration"
                                current_function.add_para(
                                    Value(
                                        parameter_name,
                                        line_number,
                                        ValueLabel.OBJ_PARA,
                                        current_function.file_path,
                                        -1,
                                    )
                                )

                            elif sub_node.type == "variadic_parameter_declaration":
                                assert (
                                    len(current_function.paras(ValueLabel.VARI_PARA))
                                    == 0
                                ), "A function can only have one variadic parameter."
                                current_function.add_para(
                                    Value(
                                        parameter_name,
                                        line_number,
                                        ValueLabel.VARI_PARA,
                                        current_function.file_path,
                                        index,
                                    )
                                )
                            else:
                                assert sub_node.type == "parameter_declaration"

                                current_function.add_para(
                                    Value(
                                        parameter_name,
                                        line_number,
                                        ValueLabel.PARA,
                                        current_function.file_path,
                                        index,
                                    )
                                )
                                index += 1

        paras = current_function.paras(ValueLabel.PARA)
        variadic_para = list(current_function.paras(ValueLabel.VARI_PARA))
        if len(variadic_para) > 0:
            assert variadic_para[0].index == len(paras), (
                f"The index of the variadic parameter should be equal to the number of parameters: "
                f"{variadic_para[0].index} != {len(paras)} in {current_function.function_name}."
            )

        return

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
    ) -> Dict[Scope, IfStatement]:
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
    ) -> Dict[Scope, LoopStatement]:
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
