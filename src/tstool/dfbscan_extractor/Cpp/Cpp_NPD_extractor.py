from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..dfbscan_extractor import *
import tree_sitter
import argparse

class Cpp_NPD_Extractor(DFBScanExtractor):
    def find_seeds(self, function: Function) -> List[Tuple[Value, bool]]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_name = function.file_path

        nodes = find_nodes_by_type(root_node, "init_declarator")
        nodes.extend(find_nodes_by_type(root_node, "assignment_expression"))
        nodes.extend(find_nodes_by_type(root_node, "return_statement"))
        nodes.extend(find_nodes_by_type(root_node, "call_expression"))

        """
        Extract the potential null values as seeds from the source code.
        1. ptr = NULL;
        2. return NULL;
        3. (type)* ptr = NULL;
        """
        spec_apis = {"malloc"}        # specific user-defined APIs that can return NULL
        seeds = []
        for node in nodes:
            is_seed_node = False
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name in spec_apis:
                            is_seed_node = True
            else:
                for child in node.children:
                    if child.type == "null":
                        is_seed_node = True

            if is_seed_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte: node.end_byte]
                seeds.append(Value(name, line_number, ValueLabel.SRC, file_name))
        return seeds
