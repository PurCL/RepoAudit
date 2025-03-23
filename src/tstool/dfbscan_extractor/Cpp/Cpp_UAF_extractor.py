from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..dfbscan_extractor import *
import tree_sitter
import argparse

class Cpp_UAF_Extractor(DFBScanExtractor):
    def find_seeds(self, function: Function) -> List[Tuple[Value, bool]]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_name = function.file_path
        
        """
        Extract the seeds for UAF Detection from the source code.
        1. free
        """
        nodes = find_nodes_by_type(root_node, "call_expression")
        nodes.extend(find_nodes_by_type(root_node, "delete_expression"))

        free_functions = {"free"}
        spec_apis = {}         # specific user-defined APIs 
        seeds = []
        for node in nodes:
            is_seed_node = False
            if node.type == "delete_expression":
                is_seed_node = True
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name in free_functions:
                            is_seed_node = True
            if is_seed_node:
                name = source_code[node.start_byte: node.end_byte]
                line_number = source_code[: node.start_byte].count("\n") + 1
                seeds.append(Value(name, line_number, ValueLabel.SRC, file_name))
        return seeds    
