import tree_sitter
from typing import List

CPP_LANGUAGE = tree_sitter.Language("build/my-languages.so", "cpp")

parser = tree_sitter.Parser()
parser.set_language(CPP_LANGUAGE)


def find_nodes(root_node: tree_sitter.Node, node_type: str) -> List[tree_sitter.Node]:
    """
    Find all the nodes with node_type type underlying the root node.
    :param root_node: root node
    :return the list of the nodes with node_type type
    """
    nodes = []
    if root_node.type == node_type:
        nodes.append(root_node)

    for child_node in root_node.children:
        nodes.extend(find_nodes(child_node, node_type))
    return nodes

with open("../benchmark/C++/toy/case01.cpp", "r") as file:
    source_code = file.read()

tree = parser.parse(bytes(source_code, "utf8"))



root = tree.root_node
all_function_nodes = []


for function_definition_node in find_nodes(tree.root_node, "function_definition"):
    for function_declaration_node in find_nodes(function_definition_node, "function_declarator"):
        function_name = ""
        for sub_node in function_declaration_node.children:
            if sub_node.type in {"identifier", "field_identifier"}:
                function_name = source_code[sub_node.start_byte:sub_node.end_byte]
                break
            elif sub_node.type == "qualified_identifier":
                qualified_function_name = source_code[sub_node.start_byte:sub_node.end_byte]
                function_name = qualified_function_name.split("::")[-1]
                break
        if function_name == "":
            continue

        # Initialize the raw data of a function
        start_line_number = source_code[: function_definition_node.start_byte].count("\n") + 1
        end_line_number = source_code[: function_definition_node.end_byte].count("\n") + 1
        print(start_line_number, end_line_number, function_name)