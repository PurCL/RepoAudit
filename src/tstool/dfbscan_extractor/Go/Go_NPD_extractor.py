from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from ..dfbscan_extractor import *
import tree_sitter
import argparse


class Go_NPD_Extractor(DFBScanExtractor):
    def is_global_source(self, global_declarator_node: Tree) -> bool:
        return False
        
    def is_global_sink(self, global_declarator_node: Tree) -> bool:
        return False
    
    def extract_sources(self, function: Function) -> List[Value]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path
        sources = []

        ## Case I: Nil value from uninitialized variables
        var_declaration_nodes = find_nodes_by_type(root_node, "var_declaration")
        for node in var_declaration_nodes:
            if len(find_nodes_by_type(node, "=")) == 0:
                line_number = source_code[: node.start_byte].count("\n") + 1
                for sub_node in node.children:
                    if sub_node.type == "var_spec":
                        for sub_sub_node in sub_node.children:
                            if sub_sub_node.type == "identifier":
                                name = source_code[
                                    sub_sub_node.start_byte : sub_sub_node.end_byte
                                ]
                                sources.append(
                                    Value(name, line_number, ValueLabel.SRC, file_path)
                                )

        ## Case II: Nil value from literal nil nodes
        literal_nil_nodes = find_nodes_by_type(root_node, "nil")
        for node in literal_nil_nodes:
            line_number = source_code[: node.start_byte].count("\n") + 1
            name = source_code[node.start_byte : node.end_byte]
            sources.append(Value(name, line_number, ValueLabel.SRC, file_path, -1))
        return sources

    def extract_sinks(self, function: Function) -> List[Value]:
        """
        Extract the sinks that can cause the null pointer dereferences from Go programs.
        :param: function: Function object.
        :return: List of sink values
        """
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path

        sink_nodes = []
        sinks = []

        for node_type in [
            "selector_expression",
            "index_expression",
            "slice_expression",
        ]:
            for node in find_nodes_by_type(root_node, node_type):
                first_child = node.children[0]
                sink_nodes.append(first_child)
                break

        for node in find_nodes_by_type(root_node, "unary_expression"):
            first_child = node.children[0]
            second_child = node.children[1]
            if first_child.type == "*":
                sink_nodes.append(second_child)

        for node in sink_nodes:
            line_number = source_code[: node.start_byte].count("\n") + 1
            name = source_code[node.start_byte : node.end_byte]
            sinks.append(Value(name, line_number, ValueLabel.SINK, file_path, -1))
        return sinks
