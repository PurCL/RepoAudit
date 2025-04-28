from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..dfbscan_extractor import *
import tree_sitter
import argparse


class Cpp_UAF_Extractor(DFBScanExtractor):
    def extract_sources(self, function: Function) -> List[Tuple[Value, bool]]:
        """
        Extract the sources that can cause the use-after-free bugs from C/C++ programs.
        :param: function: Function object.
        :return: List of source values
        """
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path

        """
        Extract the sources for UAF Detection from the source code.
        1. free
        """
        nodes = find_nodes_by_type(root_node, "call_expression")
        nodes.extend(find_nodes_by_type(root_node, "delete_expression"))

        free_functions = {"free", "ngx_destroy_black_list_link"}
        spec_apis = {}  # specific user-defined APIs
        sources = []
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
                name = source_code[node.start_byte : node.end_byte]
                line_number = source_code[: node.start_byte].count("\n") + 1
                sources.append(Value(name, line_number, ValueLabel.SRC, file_path))
        return sources

    def extract_sinks(self, function: Function) -> List[Value]:
        """
        Extract the sinks that can cause the use-after-free bugs from C/C++ programs.
        :param: function: Function object.
        :return: List of sink values
        """
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path

        """
        Extract the sinks for UAF Detection from the source code.
        1. dereference
        """
        nodes = find_nodes_by_type(root_node, "pointer_expression")
        nodes.extend(find_nodes_by_type(root_node, "field_expression"))
        nodes.extend(find_nodes_by_type(root_node, "delete_expression"))
        sinks = []

        for node in nodes:
            if node.type == "pointer_expression" and node.children[0].type != "*":
                continue
            line_number = source_code[: node.start_byte].count("\n") + 1
            name = source_code[node.start_byte : node.end_byte]
            sinks.append(Value(name, line_number, ValueLabel.SINK, file_path))
        return sinks
