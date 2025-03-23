from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..bugscan_extractor import *
import tree_sitter
import argparse


class Cpp_BOF_Extractor(BugScanExtractor):
    def find_seeds(self, function: Function) -> List[Tuple[Value, bool]]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_name = function.file_path

        nodes= find_nodes_by_type(root_node, "subscript_expression")
        nodes.extend(find_nodes_by_type(root_node, "call_expression"))
        nodes.extend(find_nodes_by_type(root_node, "pointer_expression"))

        mem_operations = {"memcpy", "memset", "memmove", "strndup"}
        mem_allocations = {"malloc", "calloc", "realloc"}
        spec_apis = {"ngx_memcpy", "ngx_sprintf"}          # specific user-defined APIs
        seeds = []
        for node in nodes:
            is_seed_node = False
            if node.type == "subscript_expression":
                is_seed_node = True
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name in mem_operations or name in mem_allocations or name in spec_apis:
                            is_seed_node = True
            if node.type == "pointer_expression" and node.children[0].type == "*":
                is_seed_node = True

            if is_seed_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte: node.end_byte]
                seeds.append((Value(name, line_number, ValueLabel.BUF_ACCESS_EXPR, file_name), True))
        return seeds
