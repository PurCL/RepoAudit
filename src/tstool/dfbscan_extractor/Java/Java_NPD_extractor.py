from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from ..dfbscan_extractor import *
import tree_sitter
import argparse

class Java_NPD_Extractor(DFBScanExtractor):
    def extract_sources(self, function: Function) -> List[Value]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path

        """
        Extract the potential null values as sources from the java source code.
        1. ptr = NULL;
        """
        null_value_nodes = find_nodes_by_type(root_node, "null_literal")

        sources = []
        for node in null_value_nodes:
            line_number = source_code[: node.start_byte].count("\n") + 1
            name = source_code[node.start_byte: node.end_byte]
            sources.append(Value(name, line_number, ValueLabel.SRC, file_path))
        return sources
    

    def extract_sinks(self, function: Function) -> List[Value]:
        """
        Extract the sinks that can cause the null pointer derferences from Java programs.
        :param: function: Function object.
        :return: List of sink values
        """
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path

        nodes = find_nodes_by_type(root_node, "method_invocation")
        nodes.extend(find_nodes_by_type(root_node, "field_access"))
        sinks = []

        for node in nodes:
            children_types = [child.type for child in node.children]
            if "." not in children_types:
                continue
            index = children_types.index(".")
            child = node.children[index - 1]
            line_number = source_code[: child.start_byte].count("\n") + 1
            name = source_code[child.start_byte : child.end_byte]
            sinks.append(Value(name, line_number, ValueLabel.SINK, file_path))
        return sinks
