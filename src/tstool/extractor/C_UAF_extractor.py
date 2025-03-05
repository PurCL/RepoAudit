from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.C_TS_analyzer import *
from .extractor import *
import tree_sitter
import argparse
import os
import json
from tqdm import tqdm

class C_UAF_Extractor(Extractor):
    def find_seed(self, source_code: str, root_node: tree_sitter.Node, file: str) -> List[LocalValue]:
        """
        Extract the seeds for UAF Detection from the source code.
        1. free
        2. delete
        """
        function_set = {"free"}
        nodes = find_nodes_by_type(root_node, "call_expression")
        nodes.extend(find_nodes_by_type(root_node, "delete_expression"))

        lines = []
        for node in nodes:
            is_sink_node = False
            if node.type == "delete_expression":
                is_sink_node = True
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name in function_set:
                            is_sink_node = True

            if is_sink_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code.split("\n")[line_number - 1]
                lines.append(LocalValue(name, line_number, ValueType.SRC, file=file))
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
    
    bof_extractor = C_UAF_Extractor(project_path, language_setting, seed_path) 
    bof_extractor.run()


if __name__ == "__main__":
    start_extract()