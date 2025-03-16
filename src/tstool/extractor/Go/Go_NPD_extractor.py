from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from ..extractor import *
import tree_sitter
import argparse
import os
import json
from tqdm import tqdm


class Go_NPD_Extractor(Extractor):
    def find_seeds(self, source_code: str, root_node: tree_sitter.Node, file_name: str) -> List[Tuple[Value, bool]]:
        """
        Extract the seeds that can cause the nil panic from the Go programs.
        :param source_code: Content of the source file.
        :param root_node: A node in the parsed syntax tree.
        :param file_path: Path of the source file.
        :return: List of the pairs of seed values and traversal strategies. True for backward, False for forward.
        """
        ## Case I: Nil value from uninitialized variables
        var_declaration_nodes = find_nodes_by_type(root_node, "var_declaration")
        seeds = []
        for node in var_declaration_nodes:
            if len(find_nodes_by_type(node, "=")) == 0:
                line_number = source_code[: node.start_byte].count("\n") + 1
                for sub_node in node.children:
                    if sub_node.type == "var_spec":
                        for sub_sub_node in sub_node.children:
                            if sub_sub_node.type == "identifier":
                                name = source_code[sub_sub_node.start_byte:sub_sub_node.end_byte]
                                seeds.append((Value(name, line_number, ValueLabel.NON_BUF_ACCESS_EXPR, file_name), False))

        ## Case II: Nil value from literal nil nodes
        literal_nil_nodes = find_nodes_by_type(root_node, "nil")
        for node in literal_nil_nodes:
            line_number = source_code[: node.start_byte].count("\n") + 1
            name = source_code[node.start_byte: node.end_byte]
            seeds.append((Value(name, line_number, ValueLabel.NON_BUF_ACCESS_EXPR, file_name), False))
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
    
    bof_extractor = Go_NPD_Extractor(project_path, language_setting, seed_path) 
    bof_extractor.run()


if __name__ == "__main__":
    start_extract()
