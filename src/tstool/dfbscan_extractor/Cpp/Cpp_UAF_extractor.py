from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..dfbscan_extractor import *
import tree_sitter
import argparse


class Cpp_UAF_Extractor(DFBScanExtractor):
    def extract_sources(self, function: Function) -> List[Value]:
        """
        Extract the sources that can cause the use-after-free bugs from C/C++ programs.
        :param: function: Function object.
        :return: List of source values
        """
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path

        nodes = find_nodes_by_type(root_node, "call_expression")
        mem_deallocations = {"free"}
        sources = []
        for node in nodes:
            is_source_node = False
            first_child = node.children[0]
            if first_child.type == "identifier":
                name = source_code[first_child.start_byte : first_child.end_byte]
                if name in mem_deallocations:
                    is_source_node = True

            if is_source_node:
                for child in node.children:
                    if child.type == "argument_list":
                        for arg in child.children[1:-1]:
                            if arg.type != ",":
                                name = source_code[arg.start_byte : arg.end_byte]
                                line_number = (
                                    source_code[: arg.start_byte].count("\n") + 1
                                )
                                if "->" in name or "." in name:
                                    continue
                                sources.append(
                                    Value(name, line_number, ValueLabel.SRC, file_path)
                                )
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
        sinks = []

        for node in find_nodes_by_type(root_node, "pointer_expression"):
            second_child = node.children[1]
            name = source_code[second_child.start_byte : second_child.end_byte]
            if name in {"this"}:
                continue
            line_number = source_code[: second_child.start_byte].count("\n") + 1
            if "->" in name or "." in name:
                continue
            sinks.append(Value(name, line_number, ValueLabel.SINK, file_path))

        for node in find_nodes_by_type(root_node, "field_expression"):
            first_child = node.children[0]
            second_child = node.children[1]
            if second_child.type == "->":
                name = source_code[first_child.start_byte : first_child.end_byte]
                if name in {"this"}:
                    continue
                line_number = source_code[: first_child.start_byte].count("\n") + 1
                if "->" in name or "." in name:
                    continue
                sinks.append(Value(name, line_number, ValueLabel.SINK, file_path))

        for node in find_nodes_by_type(root_node, "subscript_expression"):
            first_child = node.children[0]
            name = source_code[first_child.start_byte : first_child.end_byte]
            line_number = source_code[: first_child.start_byte].count("\n") + 1
            if "->" in name or "." in name:
                continue
            sinks.append(Value(name, line_number, ValueLabel.SINK, file_path))
        return sinks
