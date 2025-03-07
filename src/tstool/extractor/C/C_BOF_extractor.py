from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.C_TS_analyzer import *
from ..extractor import *
import tree_sitter
import argparse


class C_BOF_Extractor(Extractor):
    def find_seed(self, source_code: str, root_node: tree_sitter.Node, file: str) -> List[LocalValue]:
        """
        Extract the potential BOF operations from the source code.
        """
        nodes= find_nodes_by_type(root_node, "subscript_expression")
        nodes.extend(find_nodes_by_type(root_node, "call_expression"))
        nodes.extend(find_nodes_by_type(root_node, "pointer_expression"))

        mem_operations = {"memcpy", "memset", "memmove", "strndup"}
        mem_allocations = {"malloc", "calloc", "realloc"}
        spec_apis = {"ngx_memcpy"}          # specific user-defined APIs
        lines = []
        for node in nodes:
            is_src_node = False
            if node.type == "subscript_expression":
                is_src_node = True
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name in mem_operations or name in mem_allocations or name in spec_apis:
                            is_src_node = True
            if node.type == "pointer_expression" and node.children[0].type == "*":
                is_src_node = True

            if is_src_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte: node.end_byte]
                lines.append(LocalValue(name, line_number, ValueType.BUF, file=file))
        return lines
    

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
            "C++",
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
    
    bof_extractor = C_BOF_Extractor(project_path, language_setting, seed_path) 
    bof_extractor.run()


if __name__ == "__main__":
    start_extract()
