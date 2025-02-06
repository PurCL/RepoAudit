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


def print_nodes(root_node: tree_sitter.Node):
    """
    Print all the nodes in the tree with indentation.
    :param root_node: root node
    """
    print(f"Type: {root_node.type}, \t Text: {source_code[root_node.start_byte:root_node.end_byte]}")
    print("{")
    for child_node in root_node.children:
        print_nodes(child_node)
    print("}")
        


# Read the C file
with open("../benchmark/demo/deference.c", "r") as file:
    source_code = file.read()

# Parse the C code
tree = parser.parse(bytes(source_code, "utf8"))

root = tree.root_node

print_nodes(root)
            