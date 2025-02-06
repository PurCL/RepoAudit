import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
from parser.program_parser import *


class TSFunctionTransformer:
    """
    FunctionTransformer class for transforming the function into static-single-invocation (SSI) code
    and attaching the line numbers
    """

    def __init__(self, ts_analyzer) -> None:
        self.ts_analyzer = ts_analyzer

        self.SSI = ""
        self.SSI_without_comments = ""
        self.lined_SSI_function_without_comments = ""
        return

    def transform(self, function_id, source_code):
        self.hoist_method_invocation_in_argument(function_id, source_code)
        self.remove_comments_in_function()
        self.attach_line_number()
        return

    def hoist_method_invocation_in_argument(self, function_id, source_code):
        """
        Transform function to SSI form
        """
        # convert the function to SSI form.
        # The current implementation can not handle long call chains
        tree: tree_sitter.Tree = self.ts_analyzer.ts_parser.parser.parse(
            bytes(source_code, "utf8")
        )

        node = tree.root_node
        # The list of (line_number, index_number, callee_name, arg_text)
        arg_info: List[(int, int, str, str)] = []

        def process_node(node: tree_sitter.Node):
            if node.type == "method_invocation":
                for sub_node in node.children:
                    if sub_node.type == "argument_list":
                        for child in sub_node.children:
                            index = 1
                            if child.type in {"(", ")"}:
                                continue
                            sub_mi_nodes = []
                            if child.type == "method_invocation":
                                sub_mi_nodes.append(child)
                            else:
                                sub_mi_nodes = self.ts_analyzer.find_nodes(
                                    child, "method_invocation"
                                )
                            for sub_mi_node in sub_mi_nodes:
                                arg_text = source_code[
                                    sub_mi_node.start_byte : sub_mi_node.end_byte
                                ]
                                arg_line_number = (
                                    source_code[: sub_mi_node.start_byte].count("\n")
                                    + 1
                                )
                                arg_index_number = index
                                index += 1
                                arg_info.append(
                                    (arg_line_number, arg_index_number, node, arg_text)
                                )
            else:
                for sub_node in node.children:
                    process_node(sub_node)

        process_node(node)
        line_to_arg_text = {}

        for line_number, index_number, node, arg_text in arg_info:
            callee_ids = self.ts_analyzer.find_callee(function_id, source_code, node)
            if len(callee_ids) == 0:
                # Process library function calls in an adhoc way
                # The library function list needs to be extended
                type_str = ""
                if ".length()" in arg_text or ".size()" in arg_text:
                    type_str = "int"
                elif ".toString()" in arg_text:
                    type_str = "String"
                if type_str != "":
                    if line_number not in line_to_arg_text:
                        line_to_arg_text[line_number] = []
                    line_to_arg_text[line_number].append(("int", arg_text))
                continue
            callee_id = callee_ids[0]
            (
                callee_function_name,
                callee_source_code,
            ) = self.ts_analyzer.ts_parser.methods[callee_id]
            arg_list_str = callee_source_code[
                callee_source_code.find("(") + 1 : callee_source_code.find(")")
            ]
            type_name = (
                arg_list_str.split(",")[index_number - 1]
                .rstrip(" ")
                .lstrip(" ")
                .split(" ")[0]
            )
            if line_number not in line_to_arg_text:
                line_to_arg_text[line_number] = []
            line_to_arg_text[line_number].append((type_name, arg_text))

        current_line_number = 0
        source_code_lines = source_code.split("\n")
        new_source_code_lines = []
        for line_number in sorted(line_to_arg_text.keys()):
            type_arg_ls = line_to_arg_text[line_number]
            target_line_number = line_number - 1
            original_call_site_str = source_code_lines[target_line_number]
            white_space_count = len(original_call_site_str) - len(
                original_call_site_str.lstrip()
            )
            for i in range(current_line_number, target_line_number):
                new_source_code_lines.append(source_code_lines[i])
            for type_name, arg_text in type_arg_ls:
                line = (
                    type_name
                    + " "
                    + "tmp"
                    + str(self.ts_analyzer.tmp_variable_count)
                    + " = "
                    + arg_text
                    + ";"
                )
                original_call_site_str = original_call_site_str.replace(
                    arg_text, "tmp" + str(self.ts_analyzer.tmp_variable_count)
                )
                self.ts_analyzer.tmp_variable_count += 1
                new_source_code_lines.append(" " * white_space_count + line)
            new_source_code_lines.append(original_call_site_str)
            current_line_number = target_line_number + 1

        for i in range(current_line_number, len(source_code_lines)):
            new_source_code_lines.append(source_code_lines[i])

        if len(arg_info) > 0:
            self.SSI = "\n".join(new_source_code_lines)
        else:
            self.SSI = source_code
        return

    def remove_comments_in_function(self):
        # remove comments and remain the lines as blank
        # Find comment nodes and store their line numbers
        tree: tree_sitter.Tree = self.ts_analyzer.ts_parser.parser.parse(
            bytes(self.SSI, "utf8")
        )

        root_node = tree.root_node

        nodes = self.ts_analyzer.find_nodes(root_node, "line_comment")
        nodes.extend(self.ts_analyzer.find_nodes(root_node, "block_comment"))
        nodes.extend(self.ts_analyzer.find_nodes(root_node, "javadoc_comment"))

        self.SSI_without_comments = self.SSI
        for node in nodes:
            comment = self.SSI[node.start_byte : node.end_byte]
            self.SSI_without_comments = self.SSI_without_comments.replace(
                comment, "\n" * comment.count("\n")
            )
        return

    def attach_line_number(self):
        """
        :param function: Function object with the original function
        :param SSI_function: function in SSI form
        :return Function object with SSI function and lined version
        """
        new_function = (
            self.SSI_without_comments.replace("```", "").lstrip("\n").rstrip("\n")
        )
        function_content = "1. " + new_function
        line_no = 2
        self.lined_SSI_function_without_comments = ""
        for ch in function_content:
            if ch == "\n":
                self.lined_SSI_function_without_comments += "\n" + str(line_no) + ". "
                line_no += 1
            else:
                self.lined_SSI_function_without_comments += ch
        return


class TSFunctionProcessor:
    """
    FunctionProcessor class for removing comments in the function and attaching the line numbers
    """

    def __init__(self, ts_analyzer, language) -> None:
        self.ts_analyzer = ts_analyzer
        self.language = language

        self.source_code = ""
        self.code_without_comments = ""
        self.lined_code_without_comments = ""
        return

    def transform(self, source_code):
        self.source_code = source_code
        self.remove_comments_in_function()
        self.attach_line_number()
        return
    
    def remove_comments_in_function(self):
        # remove comments and remain the lines as blank
        # Find comment nodes and store their line numbers
        if self.language == 'C' or self.language == 'C++':
            tree: tree_sitter.Tree = self.ts_analyzer.ts_parser.parser.parse(
                bytes(self.source_code, "utf8")
            )
            root_node = tree.root_node

            nodes = self.ts_analyzer.find_nodes_by_type(root_node, "comment")

            self.code_without_comments = self.source_code
            for node in nodes:
                comment = self.source_code[node.start_byte : node.end_byte]
                self.code_without_comments = self.code_without_comments.replace(
                    comment, "\n" * comment.count("\n")
                )
            return
        raise ValueError("Unsupported language")

    def attach_line_number(self):
        """
        :param function: Function object with the original function
        :param SSI_function: function in SSI form
        :return Function object with SSI function and lined version
        """

        function_content = "1. " + self.code_without_comments
        line_no = 2
        self.lined_code_without_comments = ""
        for ch in function_content:
            if ch == "\n":
                self.lined_code_without_comments += "\n" + str(line_no) + ". "
                line_no += 1
            else:
                self.lined_code_without_comments += ch
        return
