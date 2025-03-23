from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from ..bugscan_extractor import *
import tree_sitter
import argparse
import os
import json
from tqdm import tqdm


class Java_NPD_Extractor(BugScanExtractor):
    def find_seeds(self, function: Function) -> List[Tuple[Value, bool]]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_name = function.file_path
        
        null_value_nodes = find_nodes_by_type(root_node, "null_literal")
        seeds = []
        for node in null_value_nodes:
            line_number = source_code[: node.start_byte].count("\n") + 1
            seeds.append((Value(source_code[node.start_byte:node.end_byte], line_number, ValueLabel.NON_BUF_ACCESS_EXPR, file_name), False))
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
            "Java"
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
    
    bof_extractor = Java_NPD_Extractor(project_path, language_setting, seed_path) 
    bof_extractor.run()


if __name__ == "__main__":
    start_extract()
