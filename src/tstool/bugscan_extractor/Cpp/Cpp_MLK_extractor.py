from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..bugscan_extractor import *
import tree_sitter
import argparse


class Cpp_MLK_Extractor(BugScanExtractor):
    def find_seeds(self, function: Function) -> List[Tuple[Value, bool]]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_name = function.file_path

        nodes = find_nodes_by_type(root_node, "call_expression")
        nodes.extend(find_nodes_by_type(root_node, "new_expression"))

        """
        Extract the seeds for Memory Leak Detection from the source code.
        1. malloc, realloc, calloc
        2. strdup, strndup
        3. asprintf, vasprintf
        4. new
        5. getline
        """
        mem_allocations = {
            "malloc",
            "calloc",
            "realloc",
            "strdup",
            "strndup",
            "asprintf",
            "vasprintf",
            "getline",
        }
        spec_apis: Set[str] = set()  # specific user-defined APIs that allocate memory
        seeds = []
        for node in nodes:
            is_seed_node = False
            if node.type == "new_expression":
                is_seed_node = True
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name in mem_allocations or name in spec_apis:
                            is_seed_node = True

            if is_seed_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte : node.end_byte]
                seeds.append(
                    (
                        Value(
                            name, line_number, ValueLabel.NON_BUF_ACCESS_EXPR, file_name
                        ),
                        False,
                    )
                )
        return seeds
