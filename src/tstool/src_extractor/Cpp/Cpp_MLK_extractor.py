from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..extractor import *
import tree_sitter
import argparse

class Cpp_MLK_Extractor(Extractor):
    def find_seeds(self, source_code: str, root_node: tree_sitter.Node, file_name: str) -> List[Tuple[Value, bool]]:
        """
        Extract the seeds that can cause the memory leak bugs from C/C++ programs.
        :param source_code: Content of the source file.
        :param root_node: A node in the parsed syntax tree.
        :param file_path: Path of the source file.
        :return: List of the pairs of seed values and traversal strategies. True for forward, False for backward.
        """
        nodes = find_nodes_by_type(root_node, "call_expression")
        nodes.extend(find_nodes_by_type(root_node, "new_expression"))

        """
        Extract the seeds for Memory Leak Detection from the source code.
        1. malloc, realloc, calloc
        2. strdup, strndup
        3. asprintf, vasprintf
        4. new
        5. getline
        """
        mem_allocations = {"malloc", "calloc", "realloc", "strdup", "strndup", "asprintf", "vasprintf", "getline"}
        spec_apis = {}          # specific user-defined APIs that allocate memory
        seeds = []
        for node in nodes:
            is_seed_node = False
            if node.type == "new_expression":
                is_seed_node = True
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name in mem_allocations or name in spec_apis:
                            is_seed_node = True

            if is_seed_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte: node.end_byte]
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
    
    ml_extractor = Cpp_MLK_Extractor(project_path, language_setting, seed_path) 
    ml_extractor.run()


if __name__ == "__main__":
    start_extract()
