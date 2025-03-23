from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from ..bugscan_extractor import *
import tree_sitter
import argparse
import os
import json
from tqdm import tqdm


class Go_BOF_Extractor(BugScanExtractor):
    def find_seeds(self, function: Function) -> List[Tuple[Value, bool]]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_name = function.file_path

        nodes= find_nodes_by_type(root_node, "index_expression")
        seeds = []
        for node in nodes:
            line_number = source_code[: node.start_byte].count("\n") + 1
            name = source_code[node.start_byte: node.end_byte]
            seeds.append((Value(name, line_number, ValueLabel.BUF_ACCESS_EXPR, file_name), True))
        return seeds
