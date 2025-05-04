from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..extractor import *
import tree_sitter
import argparse

class Cpp_NPD_Extractor(Extractor):
    def find_seeds(self, source_code: str, root_node: tree_sitter.Node, file_name: str) -> List[Tuple[Value, bool]]:
        """
        Extract the seeds that can cause the NPD bugs from the C/C++ programs.
        :param source_code: Content of the source file.
        :param root_node: A node in the parsed syntax tree.
        :param file_path: Path of the source file.
        :return: List of the pairs of seed values and traversal strategies. True for forward, False for backward.
        """
        nodes = find_nodes_by_type(root_node, "init_declarator")
        nodes.extend(find_nodes_by_type(root_node, "assignment_expression"))
        nodes.extend(find_nodes_by_type(root_node, "return_statement"))
        nodes.extend(find_nodes_by_type(root_node, "call_expression"))

        """
        Extract the potential null values as seeds from the source code.
        1. ptr = NULL;
        2. return NULL;
        3. (type)* ptr = NULL;
        """
        spec_apis = {"malloc"}        # specific user-defined APIs that can return NULL
        seeds = []
        for node in nodes:
            is_seed_node = False
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = child.text.decode("utf8")
                        if name in spec_apis:
                            is_seed_node = True
            else:
                for child in node.children:
                    if child.type == "null":
                        is_seed_node = True

            if is_seed_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = node.text.decode("utf8")
                if "\n" in name:
                    name_lines = name.split("\n")
                    for line in name_lines:
                        line = line.strip()
                    name = "".join(name_lines)
                seeds.append(Value(name, line_number, ValueLabel.SRC, file_name))
        return seeds


def start_extract():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-path",
        type=str,
        help="Specify the project path",
    )
    parser.add_argument(
        "--language",
        choices=[
            "C",
            "Cpp",
        ],
        help="Specify the language",
    )
    parser.add_argument(
        "--seed-path",
        type=str,
        help="Specify the seed path",
    )
    args = parser.parse_args()
    project_path = args.project_path
    language_setting = args.language
    seed_path = args.seed_path
    
    npd_extractor = Cpp_NPD_Extractor(project_path, language_setting, seed_path) 
    npd_extractor.run() 


if __name__ == "__main__":
    start_extract()
