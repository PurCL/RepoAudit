from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..bugscan_extractor import *
import tree_sitter
import argparse


class Cpp_UAF_Extractor(BugScanExtractor):
    def find_seeds(self, function: Function) -> List[Tuple[Value, bool]]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_name = function.file_path

        """
        Extract the seeds for UAF Detection from the source code.
        1. free
        """
        nodes = find_nodes_by_type(root_node, "call_expression")
        free_functions: Set[str] = {
            "free",
            "ngx_free",
            "ngx_mail_close_connection",
            "ngx_destroy_black_list_link",
        }
        spec_apis: Set[str] = set()  # specific user-defined APIs
        seeds = []
        for node in nodes:
            is_seed_node = False
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name in free_functions:
                            is_seed_node = True
            if is_seed_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                call_str = source_code[node.start_byte : node.end_byte]
                name = call_str.split("(")[1].split(")")[0]
                seeds.append(
                    (
                        Value(
                            name, line_number, ValueLabel.NON_BUF_ACCESS_EXPR, file_name
                        ),
                        False,
                    )
                )
        return seeds
