from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Javascript_TS_analyzer import *
from ..dfbscan_extractor import *


class Javascript_NPD_Extractor(DFBScanExtractor):
    NULLISH_VALUES = {"null", "undefined"}

    def is_expression_delete(self, expr: Node) -> bool:
        if expr.type == "unary_expression":
            operator = expr.child(0)
            if operator and operator.type == "delete":
                return True

        return False

    def is_expression_null(self, expr: Node) -> bool:
        if expr.type != "assignment_expression":
            return False

        value_node = expr.child(2)
        value_type = value_node.type if value_node else ""

        # Nullish constant (e.g. null/undefined)
        if value_type in self.NULLISH_VALUES:
            return True

        return False

    def is_global_source(self, global_declaration_node: Node) -> bool:
        # global_name is usually bytes, decode for safe string comparison
        name_node = global_declaration_node.child(1)
        if name_node is None:
            return False

        name_field = name_node.child_by_field_name("name")
        if name_field is None or name_field.text is None:
            return False

        global_name = name_field.text.decode("utf-8")

        sibling: Optional[Node] = global_declaration_node.next_sibling

        while sibling is not None:
            # Skip empty siblings
            if not sibling.children:
                sibling = sibling.next_sibling
                continue

            expr = sibling.child(0)
            if expr is None:
                sibling = sibling.next_sibling
                continue

            # Handle deletion of property
            if self.is_expression_delete(expr):
                second_child = expr.child(1)
                if second_child is not None:
                    obj_node = second_child.child_by_field_name("object")
                    if obj_node is not None and obj_node.text is not None:
                        if obj_node.text.decode("utf-8") == global_name:
                            return True

            # Handle nullish assignment
            if self.is_expression_null(expr):
                lhs = expr.child(0)
                if lhs is not None and lhs.text is not None:
                    if lhs.text.decode("utf-8") == global_name:
                        return True

            sibling = sibling.next_sibling

        return False

    def extract_sources(self, function: Function) -> List[Value]:
        """
        Extract the potential null/undefined values as sources from the source code.
        1. variable = null;
        2. return null;
        3. delete obj.prop;
        4. func(null);
        """

        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path

        nodes = find_nodes_by_type(root_node, "variable_declarator")
        nodes.extend(find_nodes_by_type(root_node, "assignment_expression"))
        nodes.extend(find_nodes_by_type(root_node, "return_statement"))
        nodes.extend(find_nodes_by_type(root_node, "arguments"))

        sources = []

        # Look for nullish value nodes
        for node in nodes:
            is_seed_node = False

            for child in node.children:
                if child.type in self.NULLISH_VALUES:
                    is_seed_node = True

            if is_seed_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte : node.end_byte]
                sources.append(Value(name, line_number, ValueLabel.SRC, file_path))

        unary_expressions = find_nodes_by_type(root_node, "unary_expression")

        # Look for delete expressions
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
        1. null_obj.prop;
        2. null_obj[1];
        3. null_obj();

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
