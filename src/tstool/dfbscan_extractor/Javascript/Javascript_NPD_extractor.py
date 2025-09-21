from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Javascript_TS_analyzer import *
from ..dfbscan_extractor import *


class Javascript_NPD_Extractor(DFBScanExtractor):
    NULLISH_VALUES = {"null", "undefined"}
    BUILTIN_NULLABLE_METHODS = {
        "exec",
        "match",
        "matchAll",
        "getElementById",
        "querySelector",
        "querySelectorAll",
        "getElementsByClassName",
        "getElementsByTagName",
        "getAttribute",
        "find",
        "findIndex",
        "pop",
        "shift",
        "get",
        "getOwnPropertyDescriptor",
        "stringify",
    }

    def is_global_source(self, global_declaration_node: Tree) -> bool:
        global_name = global_declaration_node.child(1).child_by_field_name("name").text
        sibling = global_declaration_node.next_sibling

        while sibling is not None:
            if sibling.type != "expression_statement":
                sibling = sibling.next_sibling
                continue

            expr = sibling.child(0)
            if expr.type != "assignment_expression":
                sibling = sibling.next_sibling
                continue

            if expr.child(0).text != global_name:
                sibling = sibling.next_sibling
                continue

            value_node = expr.child(2)
            value_type = value_node.type

            # Nullish constant (e.g. null/undefined)
            if value_type in self.NULLISH_VALUES:
                return True

            # Possible call expression check
            if value_type == "call_expression":
                member_expr = value_node.child(0)
                if member_expr is not None and member_expr.type == "member_expression":
                    prop_id = member_expr.child(2)
                    if (
                        prop_id is not None
                        and prop_id.type == "property_identifier"
                        and prop_id.text.decode() in self.BUILTIN_NULLABLE_METHODS
                    ):
                        return True

            return False
        return False

    def is_global_sink(self, global_declarator_node: Tree) -> bool:
        return False

    def extract_sources(self, function: Function) -> List[Value]:
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path
        null_value_nodes = []

        for nullish_value in self.NULLISH_VALUES:
            null_value_nodes.extend(find_nodes_by_type(root_node, nullish_value))

        unary_expressions = find_nodes_by_type(root_node, "unary_expression")
        call_expressions = find_nodes_by_type(root_node, "call_expression")

        sources = []

        for call_expression in call_expressions:
            member_expression = call_expression.child(0)
            if (
                member_expression is None
                or member_expression.type != "member_expression"
            ):
                continue

            property_identifier = member_expression.child(2)
            if (
                property_identifier is None
                or property_identifier.type != "property_identifier"
            ):
                continue

            if property_identifier.text.decode() in self.BUILTIN_NULLABLE_METHODS:
                line_number = (
                    source_code[: property_identifier.start_byte].count("\n") + 1
                )
                name = source_code[
                    property_identifier.start_byte : property_identifier.end_byte
                ]
                sources.append(Value(name, line_number, ValueLabel.SRC, file_path))

        for unary_expression in unary_expressions:
            operator = unary_expression.child(0)
            if operator is not None and operator.type == "delete":
                line_number = source_code[: unary_expression.start_byte].count("\n") + 1
                name = source_code[
                    unary_expression.start_byte : unary_expression.end_byte
                ]
                sources.append(Value(name, line_number, ValueLabel.SRC, file_path))

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
        nodes.extend(find_nodes_by_type(root_node, "call_expression"))
        sinks = []

        for node in nodes:
            first_child = node.children[0]
            line_number = source_code[: first_child.start_byte].count("\n") + 1
            name = source_code[first_child.start_byte : first_child.end_byte]
            sinks.append(Value(name, line_number, ValueLabel.SINK, file_path, -1))
        return sinks
