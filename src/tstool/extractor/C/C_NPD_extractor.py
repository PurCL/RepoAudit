from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.C_TS_analyzer import *
from ..extractor import *
import tree_sitter
import argparse
import os
import json
from tqdm import tqdm

class C_NPD_Extractor(Extractor):
    def find_seed(self, source_code: str, root_node: tree_sitter.Node, file: str) -> List[LocalValue]:
        """
        Extract the potential null values as seeds from the source code.
        1. ptr = NULL;
        2. return NULL;
        3. (type)* ptr = NULL;
        """
        nodes = find_nodes_by_type(root_node, "init_declarator")
        nodes.extend(find_nodes_by_type(root_node, "assignment_expression"))
        nodes.extend(find_nodes_by_type(root_node, "return_statement"))
        #lack fuction parameter

        lines = []
        for node in nodes:
            is_src_node = False
            for child in node.children:
                if child.type == "null":
                    is_src_node = True
            if is_src_node:
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
    
    npd_extractor = C_NPD_Extractor(project_path, language_setting, seed_path) 
    npd_extractor.run() 


if __name__ == "__main__":
    start_extract()
