from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..dfbscan_extractor import *
import tree_sitter
import argparse


class Cpp_NPD_Extractor(DFBScanExtractor):
    def extract_sources(self, function: Function) -> List[Value]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path

        """
        Extract the potential null values as sources from the source code.
        1. ptr = NULL;
        2. return NULL;
        3. (type)* ptr = NULL;
        """
        nodes = find_nodes_by_type(root_node, "init_declarator")
        nodes.extend(find_nodes_by_type(root_node, "assignment_expression"))
        nodes.extend(find_nodes_by_type(root_node, "return_statement"))
        nodes.extend(find_nodes_by_type(root_node, "call_expression"))

        spec_apis = {"malloc"}  # specific user-defined APIs that can return NULL
        sources = []
        for node in nodes:
            is_seed_node = False
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name in spec_apis:
                            # is_seed_node = True
                            is_seed_node = False
            else:
                for child in node.children:
                    if child.type == "null":
                        is_seed_node = True

            if is_seed_node:
                if node.type == "return_statement":
                    line_number = source_code[: node.start_byte].count("\n") + 1
                    name = source_code[node.start_byte : node.end_byte].replace("return", "").strip()
                    sources.append(Value(name, line_number, ValueLabel.SRC, file_path))
                else:
                    line_number = source_code[: node.start_byte].count("\n") + 1
                    name = source_code[node.start_byte : node.end_byte].split("=")[0].strip()
                    sources.append(Value(name, line_number, ValueLabel.SRC, file_path))
        return sources

    def extract_sinks(self, function: Function) -> List[Value]:
        """
        Extract the sinks that can cause the null pointer derferences from C/C++ programs.
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
            sinks.append(Value(name, line_number, ValueLabel.SINK, file_path))
            
        for node in find_nodes_by_type(root_node, "field_expression"):
            first_child = node.children[0]
            second_child = node.children[1]
            if second_child.type == "->":
                name = source_code[first_child.start_byte : first_child.end_byte]
                if name in {"this"}:
                    continue
                line_number = source_code[: first_child.start_byte].count("\n") + 1
                sinks.append(Value(name, line_number, ValueLabel.SINK, file_path))
        
        for node in find_nodes_by_type(root_node, "subscript_expression"):
            first_child = node.children[0]
            name = source_code[first_child.start_byte : first_child.end_byte]
            line_number = source_code[: first_child.start_byte].count("\n") + 1
            sinks.append(Value(name, line_number, ValueLabel.SINK, file_path))
        return sinks
