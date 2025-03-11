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

# Read the  python file
with open("../benchmark/Python/toy/case01.py", "r") as file:
    source_code = file.read()

# Parse the   code
tree = parser.parse(bytes(source_code, "utf8"))

root = tree.root_node
all_function_nodes = []

nodes = find_nodes(tree.root_node, "call")
paras = set()
index = 0
file_content = source_code

# for node in nodes:
#     print(source_code[:node.start_byte].count("\n") + 1)
#     for sub_node in node.children:
#         for sub_node2 in node.children:
#             if sub_node2.type == "argument_list":
#                 for sub_sub_node in sub_node2.children:
#                     print(sub_sub_node.type, source_code[sub_sub_node.start_byte:sub_sub_node.end_byte])
#         if sub_node.type == "identifier":
#             function_name = source_code[sub_node.start_byte:sub_node.end_byte]
#             break
#         if sub_node.type == "attribute":
#             for sub_sub_node in sub_node.children:
#                 if sub_sub_node.type == "identifier":
#                     function_name = source_code[sub_sub_node.start_byte:sub_sub_node.end_byte]
#             break
#     print(function_name)
#     print("=====================================")

nodes = find_nodes(tree.root_node, "function_definition")
paras = set()
index = 0
file_content = source_code

for node in nodes:
    print(source_code[:node.start_byte].count("\n"))
    for sub_node in node.children:
        if sub_node.type == "identifier":
            print(source_code[sub_node.start_byte:sub_node.end_byte])
        if sub_node.type == "parameters":
            for sub_sub_node in sub_node.children:
                for sub_node in find_nodes(sub_sub_node, "identifier"):      
                    print(source_code[sub_node.start_byte:sub_node.end_byte])  
                    break  
    print("=====================================")