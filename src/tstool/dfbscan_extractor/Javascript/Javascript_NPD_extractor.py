from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Javascript_TS_analyzer import *
from ..dfbscan_extractor import *


class Javascript_NPD_Extractor(DFBScanExtractor):
    def extract_sources(self, function: Function) -> List[Value]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path
        null_value_nodes = find_nodes_by_type(root_node, "null")
        null_value_nodes.extend(find_nodes_by_type(root_node, "undefined"))

        sources = []
        for node in null_value_nodes:
            line_number = source_code[: node.start_byte].count("\n") + 1
            name = source_code[node.start_byte : node.end_byte]
            sources.append(Value(name, line_number, ValueLabel.SRC, file_path))
            
        return sources

    def extract_sinks(self, function: Function) -> List[Value]:
        """
        Extract the sinks that can cause the null pointer dereferences from Javascript programs.
        :param: function: Function object.
        :return: List of sink values
        """
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path

        nodes = find_nodes_by_type(root_node, "member_expression")
        nodes.extend(find_nodes_by_type(root_node, "subscript_expression"))
        sinks = []

        for node in nodes:
            first_child = node.children[0]
            line_number = source_code[: first_child.start_byte].count("\n") + 1
            name = source_code[first_child.start_byte : first_child.end_byte]
            sinks.append(Value(name, line_number, ValueLabel.SINK, file_path, -1))
        return sinks
