from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..extractor import *
import tree_sitter
import argparse


class Cpp_BOF_Extractor(Extractor):
    def find_seeds(self, source_code: str, root_node: tree_sitter.Node, file_name: str) -> List[Tuple[Value, bool]]:
        """
        Extract the seeds that can cause the buffer overflow bugs from C/C++ programs.
        :param source_code: Content of the source file.
        :param root_node: A node in the parsed syntax tree.
        :param file_path: Path of the source file.
        :return: List of the pairs of seed values and traversal strategies. True for backward, False for forward.
        """
        nodes= find_nodes_by_type(root_node, "subscript_expression")
        nodes.extend(find_nodes_by_type(root_node, "call_expression"))
        nodes.extend(find_nodes_by_type(root_node, "pointer_expression"))

        mem_operations = {"memcpy", "memset", "memmove", "strndup"}
        mem_allocations = {"malloc", "calloc", "realloc"}
        spec_apis = {"ngx_memcpy", "ngx_sprintf"}          # specific user-defined APIs
        seeds = []
        for node in nodes:
            is_seed_node = False
            if node.type == "subscript_expression":
                is_seed_node = True
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name in mem_operations or name in mem_allocations or name in spec_apis:
                            is_seed_node = True
            if node.type == "pointer_expression" and node.children[0].type == "*":
                is_seed_node = True

            if is_seed_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte: node.end_byte]
                seeds.append((Value(name, line_number, ValueLabel.BUF_ACCESS_EXPR, file_name), True))
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
    
    bof_extractor = Cpp_BOF_Extractor(project_path, language_setting, seed_path) 
    bof_extractor.run()


if __name__ == "__main__":
    start_extract()
