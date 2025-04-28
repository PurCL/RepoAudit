from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from ..dfbscan_extractor import *
import tree_sitter
import argparse

class Go_NPD_Extractor(DFBScanExtractor):    
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
                                name = source_code[sub_sub_node.start_byte:sub_sub_node.end_byte]
                                sources.append(Value(name, line_number, ValueLabel.SRC, file_path))

        ## Case II: Nil value from literal nil nodes
        literal_nil_nodes = find_nodes_by_type(root_node, "nil")
        for node in literal_nil_nodes:
            line_number = source_code[: node.start_byte].count("\n") + 1
            name = source_code[node.start_byte: node.end_byte]
            sources.append(Value(name, line_number, ValueLabel.SRC, file_path))
        return sources
    
    
    def extract_sinks(self, function: Function) -> List[Value]:
        """
        Extract the sinks that can cause the null pointer derferences from Go programs.
        :param: function: Function object.
        :return: List of sink values
        """
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path

        nodes = find_nodes_by_type(root_node, "selector_expression")
        # nodes = find_nodes_by_type(root, "index_expression")
        # nodes = find_nodes_by_type(root, "slice_expression")
        # nodes = find_nodes_by_type(root, "unary_expression")
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
