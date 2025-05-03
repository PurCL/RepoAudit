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

with open("../benchmark/Cpp/toy/test.cpp", "r") as file:
    source_code = file.read()

tree = parser.parse(bytes(source_code, "utf8"))



root = tree.root_node
all_function_nodes = []

nodes = find_nodes(root, "call_expression")

for node in nodes:
    first_child = node.children[0]
    print(source_code[first_child.start_byte : first_child.end_byte])
