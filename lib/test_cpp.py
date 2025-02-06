import tree_sitter
from typing import List

C_LANGUAGE = tree_sitter.Language("build/my-languages.so", "cpp")

parser = tree_sitter.Parser()
parser.set_language(C_LANGUAGE)


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

with open("../benchmark/C++/demo/01.cpp", "r") as file:
    source_code = file.read()

tree = parser.parse(bytes(source_code, "utf8"))

root = tree.root_node
all_function_nodes = []

all_function_definition_nodes = find_nodes(tree.root_node, "parameter_declaration")

for node in all_function_definition_nodes:
    for sub_target in node.children:
        print(sub_target.type)
