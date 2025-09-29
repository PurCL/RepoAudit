from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Javascript_TS_analyzer import *
from ..dfbscan_extractor import *


class Javascript_UAF_Extractor(DFBScanExtractor):
    def is_global_source(self, global_declaration_node: Node) -> bool:
        """
        Determine if this global variable is a UAF source.
        A UAF source is a global variable that has *one of its attributes*
        deleted somewhere later at the top-level scope.
        """
        # 1. Get the declared variable's name
        name_node = global_declaration_node.child(1).child_by_field_name("name")
        if name_node is None:
            return False
        global_name = (
            name_node.text.decode("utf8")
            if isinstance(name_node.text, bytes)
            else name_node.text
        )

        sibling = global_declaration_node.next_sibling
        while sibling is not None:
            # Look for unary_expression nodes whose operator is 'delete'
            for descendant in sibling.children:
                if descendant.type == "unary_expression":
                    operator = descendant.child(0)
                    if operator and operator.type == "delete":
                        # The next child should be the expression being deleted
                        target = descendant.child(1)
                        if target and target.type == "member_expression":
                            # Check that the object part of member_expression matches our global variable
                            obj_node = target.child_by_field_name("object")
                            if obj_node:
                                obj_name = (
                                    obj_node.text.decode("utf8")
                                    if isinstance(obj_node.text, bytes)
                                    else obj_node.text
                                )
                                if obj_name == global_name:
                                    return True
            sibling = sibling.next_sibling

        return False

    def is_global_sink(self, global_declarator_node: Tree) -> bool:
        return False

    def extract_sources(self, function: Function) -> List[Value]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path

        unary_expressions = find_nodes_by_type(root_node, "unary_expression")
        sources = []

        for unary_expression in unary_expressions:
            operator = unary_expression.child(0)
            if operator is not None and operator.type == "delete":
                line_number = source_code[: unary_expression.start_byte].count("\n") + 1
                name = source_code[
                    unary_expression.start_byte : unary_expression.end_byte
                ]
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
        nodes.extend(find_nodes_by_type(root_node, "call_expression"))
        sinks = []

        for node in nodes:
            first_child = node.children[0]
            line_number = source_code[: first_child.start_byte].count("\n") + 1
            name = source_code[first_child.start_byte : first_child.end_byte]
            sinks.append(Value(name, line_number, ValueLabel.SINK, file_path, -1))
        return sinks
