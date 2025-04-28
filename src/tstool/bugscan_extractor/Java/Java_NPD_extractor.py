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
            seeds.append(
                (
                    Value(
                        source_code[node.start_byte : node.end_byte],
                        line_number,
                        ValueLabel.NON_BUF_ACCESS_EXPR,
                        file_name,
                    ),
                    False,
                )
            )
        return seeds
