import tree_sitter
from typing import List

C_LANGUAGE = tree_sitter.Language("build/my-languages.so", "java")

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

# Read the Java file
with open("../benchmark/Java/demo/01.java", "r") as file:
    source_code = file.read()

# Parse the Java code
tree = parser.parse(bytes(source_code, "utf8"))

root = tree.root_node
all_function_nodes = []

for_nodes = find_nodes(root, "for_statement")
for_nodes.extend(find_nodes(root, "enhanced_for_statement"))
while_nodes = find_nodes(root, "while_statement")

for node in for_nodes:
    for sub_node in node.children:
        print(sub_node.type)
        print(source_code[sub_node.start_byte:sub_node.end_byte])
        print("")
