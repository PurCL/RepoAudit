from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from ..extractor import *
import tree_sitter
import argparse
import os
import json
from tqdm import tqdm


class Go_NPD_Extractor(Extractor):
    def find_seed(self, source_code: str, root_node: tree_sitter.Node, file: str) -> List[LocalValue]:
        """
        Extract the possible forms of nil values for Nil Panic detection from the source code.
        """
        ## Case I: Nil value from uninitialized variables
        var_declaration_nodes = find_nodes_by_type(root_node, "var_declaration")
        lines = []
        for node in var_declaration_nodes:
            if len(find_nodes_by_type(node, "=")) == 0:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte: node.end_byte]
                lines.append(LocalValue(name, line_number, ValueType.SRC, file=file))

        ## Case II: Nil value from literal nil nodes
        literal_nil_nodes = find_nodes_by_type(root_node, "nil")
        for node in literal_nil_nodes:
            line_number = source_code[: node.start_byte].count("\n") + 1
            name = source_code[node.start_byte: node.end_byte]
            lines.append(LocalValue(name, line_number, ValueType.SRC, file=file))

        ## Case III: missing returned values
        return_statement_nodes = find_nodes_by_type(root_node, "return_statement")
        return_statements_with_num = []
        for return_statement_node in return_statement_nodes:
            for sub_node in return_statement_node.children:
                if sub_node.type == "expression_list":
                    return_statements_with_num.append((return_statement_node, len(sub_node.children)))
            sub_node_types = [sub_node.type for sub_node in return_statement_node.children]
            if "expression_list" not in sub_node_types:
                line_number = source_code[: return_statement_node.start_byte].count("\n") + 1
                name = source_code[return_statement_node.start_byte: return_statement_node.end_byte]
                lines.append(LocalValue(name, line_number, ValueType.SRC, file=file))

        # select the largest number of return values
        if len(return_statements_with_num) > 0:
            return_statement_node, max_num = max(return_statements_with_num, key=lambda x: x[1])
            for (return_statement_node, num) in return_statements_with_num:
                if num < max_num:
                    line_number = source_code[: return_statement_node.start_byte].count("\n") + 1
                    name = source_code[return_statement_node.start_byte: return_statement_node.end_byte]
                    lines.append(LocalValue(name, line_number, ValueType.SRC, file=file))
        return lines
    

def start_extract():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-path",
        type=str,
        help="Specify the project path",
    )
    parser.add_argument(
        "--language",
        choices=[
            "Go"
        ],
        help="Specify the language",
    )
    parser.add_argument(
        "--seed-path",
        type=str,
        help="Specify the seed path",
    )
    args = parser.parse_args()
    project_path = args.project_path
    language_setting = args.language
    seed_path = args.seed_path
    
    bof_extractor = Go_NPD_Extractor(project_path, language_setting, seed_path) 
    bof_extractor.run()


if __name__ == "__main__":
    start_extract()
