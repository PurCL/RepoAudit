from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from ..bugscan_extractor import *
import tree_sitter
import argparse
import os
import json
from tqdm import tqdm


class Go_NPD_Extractor(BugScanExtractor):
    def find_seeds(self, function: Function) -> List[Tuple[Value, bool]]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_name = function.file_path
        
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
