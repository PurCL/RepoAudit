from parser.base_parser import *
import tree_sitter
from utility.localvalue import *
from typing import List

def find_invocation_sites(source_code: str, root_node: tree_sitter.Node, src_functions: set, file: str) -> List[LocalValue]:
    """
    Find the invocation sites of the source functions.
    """
    nodes = find_nodes_by_type(root_node, "call_expression")
    nodes.extend(find_nodes_by_type(root_node, "macro_type_specifier"))

    lines = []
    for node in nodes:
        is_src_node = False
        for child in node.children:
            if child.type == "identifier":
                name = source_code[child.start_byte : child.end_byte]
                if name in src_functions:
                    is_src_node = True

        if is_src_node:
            line_number = source_code[: node.start_byte].count("\n") + 1
            name = source_code.split("\n")[line_number - 1]
            lines.append(LocalValue(name, line_number, ValueType.SRC, file=file))
    return lines