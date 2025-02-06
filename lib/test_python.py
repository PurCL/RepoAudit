import tree_sitter
from typing import List

C_LANGUAGE = tree_sitter.Language("build/my-languages.so", "python")

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
with open("../benchmark/Python/demo/01.py", "r") as file:
    source_code = file.read()

# Parse the Java code
tree = parser.parse(bytes(source_code, "utf8"))

root = tree.root_node
all_function_nodes = []

parameters = find_nodes(tree.root_node, "parameters")
paras = set()
index = 0
file_content = source_code

for parameter_node in parameters:
    for parameter in parameter_node.children:
        print(parameter.type)
        if parameter.type == "identifier":
            parameter_name = file_content[parameter.start_byte:parameter.end_byte]
            line_number = file_content[:parameter.start_byte].count("\n") + 1
            paras.add((parameter_name, line_number, index))
            print((parameter_name, line_number, index))
            index += 1
        elif parameter.type == "typed_parameter":
            para_identifier_node = parameter.children[0]
            parameter_name = file_content[para_identifier_node.start_byte:para_identifier_node.end_byte]
            line_number = file_content[:para_identifier_node.start_byte].count("\n") + 1
            paras.add((parameter_name, line_number, index))
            print((parameter_name, line_number, index))
            index += 1