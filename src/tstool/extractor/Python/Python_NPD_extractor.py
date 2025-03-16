from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *
from ..extractor import *
import tree_sitter
import argparse
import os
import json
from tqdm import tqdm


class Python_NPD_Extractor(Extractor):
    def find_seeds(self, source_code: str, root_node: tree_sitter.Node, file_name: str) -> List[Tuple[Value, bool]]:
        """
        Extract the seeds that can cause the NPE from the Python programs.
        :param source_code: Content of the source file.
        :param root_node: A node in the parsed syntax tree.
        :param file_path: Path of the source file.
        :return: List of the pairs of seed values and traversal strategies. True for backward, False for forward.
        """
        null_value_nodes = find_nodes_by_type(root_node, "none")
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
            "Python"
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
    
    bof_extractor = Python_NPD_Extractor(project_path, language_setting, seed_path) 
    bof_extractor.run()


if __name__ == "__main__":
    start_extract()
