from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from .extractor import *
import tree_sitter
import argparse
import os
import json
from tqdm import tqdm


class Go_BOF_Extractor(Extractor):
    def find_seed(self, source_code: str, root_node: tree_sitter.Node, file: str) -> List[LocalValue]:
        """
        Extract the potential BOF operations from the source code.
        """
        nodes= find_nodes_by_type(root_node, "index_expression")
        lines = []
        for node in nodes:
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
            "Go"
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
    
    bof_extractor = Go_BOF_Extractor(project_path, language_setting, seed_path) 
    bof_extractor.run()


if __name__ == "__main__":
    start_extract()
