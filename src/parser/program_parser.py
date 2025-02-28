import os
import sys
from os import path
from pathlib import Path
from typing import List, Tuple, Dict, Set

import tree_sitter
from tree_sitter import Language
from tqdm import tqdm
import networkx as nx

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

from typing import List, Tuple, Dict
from utility.localvalue import *
from utility.function import *


class TSParser:
    """
    TSParser class for extracting information from source files using tree-sitter.
    """

    def __init__(self, code_in_projects: Dict[str, str], language_setting: str) -> None:
        """
        Initialize TSParser with a collection of source files.
        :param code_in_projects: A dictionary containing the content of source files.
        """
        self.code_in_projects = code_in_projects
        self.language_setting = language_setting

        self.functionRawDataDic = {}
        self.functionNameToId = {}
        self.functionToFile = {}
        self.fileContentDic = {}
        self.macro_map = {}

        cwd = Path(__file__).resolve().parent.absolute()
        TSPATH = cwd / "../../lib/build/"
        language_path = TSPATH / "my-languages.so"

        # Initialize the parser
        self.parser = tree_sitter.Parser()

        # initilize the language according to language_setting
        if language_setting == "C":
            self.language = Language(str(language_path), "c")
        elif language_setting == "C++":
            self.language = Language(str(language_path), "cpp")
        elif language_setting == "Java":
            self.language = Language(str(language_path), "java")
        elif language_setting == "Python":
            self.language = Language(str(language_path), "python")

        self.parser.set_language(self.language)


    def parse_function_info(self, file_path: str, source_code: str, tree: tree_sitter.Tree) -> None:
        """
        Parse the function information in a source file.
        :param file_path: The path of the source file.
        :param source_code: The content of the source file.
        :param tree: The parse tree of the source file.
        """
        all_function_header_nodes = []

        """
        Currently, we only handle four languages: C, C++, Java, and Python.
        """
        if self.language_setting in ["C", "C++"]:
            all_function_header_nodes = []
            all_function_definition_nodes = TSAnalyzer.find_nodes_by_type(tree.root_node, "function_definition")
            for function_definition_node in all_function_definition_nodes:
                all_function_header_nodes.extend(TSAnalyzer.find_nodes_by_type(function_definition_node, "function_declarator"))

            # for function_definitino_node in all_function_definition_nodes:
            #     for sub_node in function_definitino_node.children:
            #         if sub_node.type == "function_declarator":
            #             all_function_header_nodes.append(sub_node)
        elif self.language_setting in ["Java"]:
            all_function_header_nodes = TSAnalyzer.find_nodes_by_type(tree.root_node, "method_declaration")
        elif self.language_setting in ["Python"]:
            all_function_header_nodes = TSAnalyzer.find_nodes_by_type(tree.root_node, "function_definition")
        else:
            assert "Wrong language setting"                 
    
        for node in all_function_header_nodes:
            function_name = ""
            for sub_node in node.children:
                if sub_node.type == "identifier":
                    function_name = source_code[sub_node.start_byte:sub_node.end_byte]
                    break
                elif sub_node.type == "qualified_identifier":
                    qualified_function_name = source_code[sub_node.start_byte:sub_node.end_byte]
                    function_name = qualified_function_name.split("::")[-1]

            if function_name == "":
                continue
            
            function_node = node.parent if self.language_setting in ["C", "C++"] else node

            if self.language_setting in ["C", "C++"]:
                is_function_definition = True
                while True:
                    if function_node.type == "function_definition":
                        break
                    function_node = function_node.parent
                    if function_node is None:
                        is_function_definition = False
                        break
                    if "statement" in function_node.type:
                        is_function_definition = False
                        break
                if not is_function_definition:
                    continue

            # Initialize the raw data of a function
            start_line_number = source_code[: function_node.start_byte].count("\n") + 1
            end_line_number = source_code[: function_node.end_byte].count("\n") + 1
            function_id = len(self.functionRawDataDic) + 1
            
            self.functionRawDataDic[function_id] = (
                function_name,
                start_line_number,
                end_line_number,
                function_node
            )
            self.functionToFile[function_id] = file_path
            
            if function_name not in self.functionNameToId:
                self.functionNameToId[function_name] = set([])
            self.functionNameToId[function_name].add(function_id)
        return
    

    def parse_macro_info(self, file_path: str, source_code: str, tree: tree_sitter.Tree) -> None:
        """
        Parse the global variable information in a source file.
        :param file_path: The path of the source file.
        :param source_code: The content of the source file.
        :param tree: The parse tree of the source file.
        """
        # TODO: only support C/C++ now
        if not self.language_setting in ["C", "C++"]:
            return
        all_macro_nodes = TSAnalyzer.find_nodes_by_type(tree.root_node, "preproc_def")

        for node in all_macro_nodes:
            macro_name = ""
            macro_definition = ""
            for child in node.children:
                if child.type == "identifier":
                    macro_name = source_code[child.start_byte:child.end_byte]
                if child.type == "preproc_arg":
                    macro_definition = source_code[child.start_byte:child.end_byte]
            if macro_name != "" and macro_definition != "":
                self.macro_map[macro_name] = macro_definition
        
        all_macro_nodes = TSAnalyzer.find_nodes_by_type(tree.root_node, "preproc_function_def")

        for node in all_macro_nodes:
            function_name = ""
            for child in node.children:
                if child.type == "identifier":
                    function_name = source_code[child.start_byte:child.end_byte]
                if child.type == "preproc_params":
                    function_name += source_code[child.start_byte:child.end_byte]
            if function_name == "":
                continue
            function_node = node
            start_line_number = source_code[: function_node.start_byte].count("\n") + 1
            end_line_number = source_code[: function_node.end_byte].count("\n") + 1
            function_id = len(self.functionRawDataDic) + 1
            
            self.functionRawDataDic[function_id] = (
                function_name,
                start_line_number,
                end_line_number,
                function_node
            )
            self.functionToFile[function_id] = file_path
            
            if function_name not in self.functionNameToId:
                self.functionNameToId[function_name] = set([])
            self.functionNameToId[function_name].add(function_id)

        return


    def parse_project(self) -> None:
        """
        Parse the project.
        """
        pbar = tqdm(total=len(self.code_in_projects), desc="Parsing files")
        for file_path in self.code_in_projects:
            pbar.update(1)
            source_code = self.code_in_projects[file_path]
            tree = self.parser.parse(bytes(source_code, "utf8"))
            self.parse_function_info(file_path, source_code, tree)
            self.parse_macro_info(file_path, source_code, tree)
            self.fileContentDic[file_path] = source_code
        return


class TSAnalyzer:
    """
    TSAnalyzer class for retrieving necessary facts or functions for LMAgent
    """

    def __init__(
        self,
        code_in_projects: Dict[str, str],
        language: str,
    ) -> None:
        """
        Initialize TSParser with the project path.
        :param code_in_projects: A dictionary mapping file paths of source files to their contents
        """
        self.code_in_projects = code_in_projects
        self.ts_parser = TSParser(self.code_in_projects, language)
        self.ts_parser.parse_project()

        # Each funcntion in the environments maintains the local meta data, including
        # (1) AST node type analysis
        # (2) intraprocedural control flow analysis
        self.environment = {}  

        # Macro variable map
        self.macro_map = self.ts_parser.macro_map

        # Results of call graph analysis
        self.caller_callee_map = {}
        self.callee_caller_map = {}
        self.call_graph = nx.DiGraph()

        pbar = tqdm(total=len(self.ts_parser.functionRawDataDic), desc="Analyzing functions")
        for function_id in self.ts_parser.functionRawDataDic:
            pbar.update(1)
            (name, start_line_number, end_line_number, function_node) = (
                self.ts_parser.functionRawDataDic[function_id]
            )
            file_name = self.ts_parser.functionToFile[function_id]
            file_content = self.ts_parser.fileContentDic[file_name]
            function_code = file_content[function_node.start_byte:function_node.end_byte]
            current_function = Function(
                function_id, name, function_code, start_line_number, end_line_number, function_node, file_name
            )
            current_function = self.extract_meta_data_in_single_function(current_function, file_content)
            self.environment[function_id] = current_function
        pbar.close()

        pbar = tqdm(total=len(self.ts_parser.functionRawDataDic), desc="Analyzing call graphs")
        for function_id in self.environment:
            pbar.update(1)
            current_function = self.environment[function_id]
            file_content = self.ts_parser.fileContentDic[current_function.file_name]
            self.extract_call_graph(current_function, file_content)
        pbar.close()

        # initialize call graph
        for caller_id in self.caller_callee_map:
            for callee_id in self.caller_callee_map[caller_id]:
                self.call_graph.add_edge(caller_id, callee_id)
        return
    

    def extract_meta_data_in_single_function(
        self, current_function: Function, file_content: str
    ) -> Function:
        """
        Extract meta data in a single function
        :param current_function: the function to be analyzed
        :param file_content: the content of the file
        """
        # AST node type analysis
        current_function.paras = self.find_paras(current_function, file_content)
        current_function.retsmts = self.find_retstmts(current_function, file_content)

        # Intraprocedural control flow analysis
        current_function.if_statements = self.find_if_statements(
            file_content,
            current_function.parse_tree_root_node,
        )

        current_function.loop_statements = self.find_loop_statements(
            file_content,
            current_function.parse_tree_root_node,
        )

        return current_function
    
    def extract_call_graph(self, current_function: Function, file_content: str):
        """
        Extract the call graph.
        :param current_function: the function to be analyzed
        :param file_content: the content of the file
        """
        # Over-approximate the caller-callee relationship via function names, achieved by find_callee
        function_call_node_type = ""
        if self.ts_parser.language_setting in ["C", "C++"]:
            function_call_node_type = "call_expression"
        elif self.ts_parser.language_setting in ["Java"]:
            function_call_node_type = "method_invocation"
        elif self.ts_parser.language_setting in ["Python"]:
            function_call_node_type = "call"

        all_call_sites = self.find_nodes_by_type(current_function.parse_tree_root_node, function_call_node_type)
        white_call_sites = []

        for call_site_node in all_call_sites:
            callee_ids = self.find_callee(file_content, call_site_node)
            if len(callee_ids) > 0:
                # Update the call graph
                for callee_id in callee_ids:
                    caller_id = current_function.function_id
                    if caller_id not in self.caller_callee_map:
                        self.caller_callee_map[caller_id] = set([])
                    self.caller_callee_map[caller_id].add(callee_id)
                    if callee_id not in self.callee_caller_map:
                        self.callee_caller_map[callee_id] = set([])
                    self.callee_caller_map[callee_id].add(caller_id)
                white_call_sites.append(call_site_node)

        current_function.call_site_nodes = white_call_sites
        return

    #################################################
    ########## Call Graph Analysis ##################
    #################################################
    @staticmethod
    def get_callee_name_at_call_site(node: tree_sitter.Node, source_code: str, language: str) -> str:
        """
        Get the callee name at the call site.
        :param node: the node of the call site
        :param source_code: the content of the file
        :param language: the language of the source code
        """
        if language in ["C", "C++", "Java"]:
            sub_sub_nodes = []
            for sub_node in node.children:
                if sub_node.type == "identifier":
                    sub_sub_nodes.append(sub_node)
                else:
                    for sub_sub_node in sub_node.children:
                        sub_sub_nodes.append(sub_sub_node)
                break
            sub_sub_node_types = [source_code[sub_sub_node.start_byte:sub_sub_node.end_byte] for sub_sub_node in sub_sub_nodes]  
            if len(sub_sub_node_types) == 0:
                return ""
            index_of_last_dot = len(sub_sub_node_types) - 1 - sub_sub_node_types[::-1].index(".") if "." in sub_sub_node_types else -1
            index_of_last_arrow = len(sub_sub_node_types) - 1 - sub_sub_node_types[::-1].index("->") if "->" in sub_sub_node_types else -1
            function_name = sub_sub_node_types[max(index_of_last_dot, index_of_last_arrow) + 1]
            return function_name
        elif language in ["Python"]:
            for sub_node in node.children:
                if sub_node.type == "attribute":
                    for sub_sub_node in reversed(sub_node.children):
                        if sub_sub_node.type == "identifier":
                            return source_code[sub_sub_node.start_byte:sub_sub_node.end_byte]
        return ""
    
    @staticmethod
    def get_arguments_at_call_site(node: tree_sitter.Node, source_code: str) -> List[str]:
        """
        Get arguments at the call site.
        :param node: the node of the call site
        :param source_code: the content of the file
        """
        arguments = []
        for sub_node in node.children:
            if sub_node.type == "argument_list":
                arg_list = sub_node.children[1:-1]
                for element in arg_list:
                    if element.type != ",":
                        arguments.append(source_code[element.start_byte:element.end_byte])
        return arguments
    

    def find_callee(self, file_content: str, call_site_node: tree_sitter.Node) -> List[int]:
        """
        Find the callee function of the call site.
        :param file_content: the content of the file
        :param call_site_node: the node of the call site
        """
        callee_name = self.get_callee_name_at_call_site(call_site_node, file_content, self.ts_parser.language_setting)
        arguments = self.get_arguments_at_call_site(call_site_node, file_content)
        temp_callee_ids = []
        # support macro defination
        while callee_name in self.ts_parser.macro_map:
            callee_name = self.ts_parser.macro_map[callee_name]
        if callee_name in self.ts_parser.functionNameToId:
            temp_callee_ids.extend(list(self.ts_parser.functionNameToId[callee_name]))
        # check parameter number and the argument number
        callee_ids = []
        for callee_id in temp_callee_ids:
            callee = self.environment[callee_id]
            paras = self.find_paras(callee, file_content)
            if len(paras) == len(arguments):
                callee_ids.append(callee_id)
        return callee_ids

    #################################################
    ########## AST Node Type Analysis ###############
    #################################################   

    # The following three versions para-extraction functions may be verbose and redundant
    # However, we keep them as they may need to be extended for more complex cases separately in the future

    def find_paras(self, current_function: Function, file_content: str) -> Set[Tuple[str, int, int]]:
        """
        Find the parameters in the function.
        :param file_content: the content of the file
        :param node: the node of the function
        """
        if self.ts_parser.language_setting in ["C", "C++"]:
            return self.extract_paras_in_C_CPP(current_function, file_content)
        elif self.ts_parser.language_setting in ["Java"]:
            return self.extract_paras_in_Java(current_function, file_content)
        elif self.ts_parser.language_setting in ["Python"]:
            return self.extract_paras_in_Python(current_function, file_content)
        return set([])


    def extract_paras_in_C_CPP(self, current_function: Function, file_content: str) -> Set[Tuple[str, int, int]]:
        paras = set([])
        parameters = self.find_nodes_by_type(current_function.parse_tree_root_node, "parameter_declaration")
        parameters.extend(self.find_nodes_by_type(current_function.parse_tree_root_node, "preproc_params"))
        index = 0
        for parameter_node in parameters:
            for sub_node in TSAnalyzer.find_nodes_by_type(parameter_node, "identifier"):                
                parameter_name = file_content[sub_node.start_byte:sub_node.end_byte]
                line_number = file_content[:sub_node.start_byte].count("\n") + 1
                paras.add((parameter_name, line_number, index))
                index += 1
        return paras


    def extract_paras_in_Java(self, current_function: Function, file_content: str) -> Set[Tuple[str, int, int]]:
        paras = set([])
        parameters = self.find_nodes_by_type(current_function.parse_tree_root_node, "formal_parameter")
        index = 0
        for parameter_node in parameters:
            for sub_node in TSAnalyzer.find_nodes_by_type(parameter_node, "identifier"):                
                parameter_name = file_content[sub_node.start_byte:sub_node.end_byte]
                line_number = file_content[:sub_node.start_byte].count("\n") + 1
                paras.add((parameter_name, line_number, index))
                index += 1
        return paras
    

    def extract_paras_in_Python(self, current_function: Function, file_content: str) -> Set[Tuple[str, int, int]]:
        paras = set([])
        parameters = self.find_nodes_by_type(current_function.parse_tree_root_node, "parameters")
        index = 0
        for parameter_node in parameters:
            for parameter in parameter_node.children:
                if parameter.type == "identifier":
                    parameter_name = file_content[parameter.start_byte:parameter.end_byte]
                    line_number = file_content[:parameter.start_byte].count("\n") + 1
                    paras.add((parameter_name, line_number, index))
                    index += 1
                elif parameter.type == "typed_parameter":
                    para_identifier_node = parameter.children[0]
                    parameter_name = file_content[para_identifier_node.start_byte:para_identifier_node.end_byte]
                    line_number = file_content[:para_identifier_node.start_byte].count("\n") + 1
                    paras.add((parameter_name, line_number, index))
                    index += 1
        return paras
    
    def find_retstmts(self, current_function: Function, file_content: str) -> List[Tuple[str, int]]:
        """
        Find the return statements in the function.
        :param current_function: the function to be analyzed
        :param file_content: the content of the file
        """
        retstmts = []
        retnodes = self.find_nodes_by_type(current_function.parse_tree_root_node, "return_statement")
        for retnode in retnodes:
            line_number = file_content[:retnode.start_byte].count("\n") + 1
            retstmts.append((retnode, line_number))
        return retstmts


    #################################################
    ########## Control Flow Analysis ################
    #################################################

    # The following three versions if-statement meta-data extraction functions may be verbose and redundant
    # However, we keep them as they may need to be extended for more complex cases separately in the future

    @staticmethod
    def extract_meta_data_of_Java_if_statements(source_code, root_node) -> Dict[Tuple, Tuple]:
        """
        Extract meta data of if statements in Java
        """
        if_statement_nodes = TSAnalyzer.find_nodes_by_type(root_node, "if_statement")
        if_statements = {}

        for if_statement_node in if_statement_nodes:
            condition_str = ""
            condition_start_line = 0
            condition_end_line = 0
            true_branch_start_line = 0
            true_branch_end_line = 0
            else_branch_start_line = 0
            else_branch_end_line = 0

            block_num = 0
            for sub_target in if_statement_node.children:
                if sub_target.type == "parenthesized_expression":
                    condition_start_line = (
                        source_code[: sub_target.start_byte].count("\n") + 1
                    )
                    condition_end_line = (
                        source_code[: sub_target.end_byte].count("\n") + 1
                    )
                    condition_str = source_code[
                        sub_target.start_byte : sub_target.end_byte
                    ]
                if sub_target.type == "block":
                    lower_lines = []
                    upper_lines = []
                    for sub_sub_target in sub_target.children:
                        if sub_sub_target.type not in {"{", "}"}:
                            lower_lines.append(source_code[: sub_sub_target.start_byte].count("\n") + 1)
                            upper_lines.append(source_code[: sub_sub_target.end_byte].count("\n") + 1)
                    if len(upper_lines) == 0 or len(lower_lines) == 0:
                        continue
                    
                    if block_num == 0:
                        true_branch_start_line = min(lower_lines)
                        true_branch_end_line = max(upper_lines)
                        block_num += 1
                    elif block_num == 1:
                        else_branch_start_line = min(lower_lines)
                        else_branch_end_line = max(upper_lines)
                        block_num += 1
                if sub_target.type == "expression_statement":
                    true_branch_start_line = source_code[: sub_target.start_byte].count("\n") + 1
                    true_branch_end_line = source_code[: sub_target.end_byte].count("\n") + 1
                    
            if_statement_start_line = source_code[: if_statement_node.start_byte].count("\n") + 1
            if_statement_end_line = source_code[: if_statement_node.end_byte].count("\n") + 1
            line_scope = (if_statement_start_line, if_statement_end_line)
            info = (
                        condition_start_line,
                        condition_end_line,
                        condition_str,
                        (true_branch_start_line, true_branch_end_line),
                        (else_branch_start_line, else_branch_end_line),
                    )
            if_statements[line_scope] = info 
        return if_statements
    

    @staticmethod
    def extract_meta_data_of_C_CPP_if_statements(source_code, root_node) -> Dict[Tuple, Tuple]:
        """
        Extract meta data of if statements in C/C++
        """
        if_statement_nodes = TSAnalyzer.find_nodes_by_type(root_node, "if_statement")
        if_statements = {}

        for if_statement_node in if_statement_nodes:
            condition_str = ""
            condition_start_line = 0
            condition_end_line = 0
            true_branch_start_line = 0
            true_branch_end_line = 0
            else_branch_start_line = 0
            else_branch_end_line = 0

            for sub_target in if_statement_node.children:
                if sub_target.type in ["parenthesized_expression", "condition_clause"]:
                    condition_start_line = (
                        source_code[: sub_target.start_byte].count("\n") + 1
                    )
                    condition_end_line = (
                        source_code[: sub_target.end_byte].count("\n") + 1
                    )
                    condition_str = source_code[
                        sub_target.start_byte : sub_target.end_byte
                    ]
                if "statement" in sub_target.type:
                    true_branch_start_line = (
                        source_code[: sub_target.start_byte].count("\n") + 1
                    )
                    true_branch_end_line = (
                        source_code[: sub_target.end_byte].count("\n") + 1
                    )
                if sub_target.type == "else_clause":
                    else_branch_start_line = (
                        source_code[: sub_target.start_byte].count("\n") + 1
                    )
                    else_branch_end_line = (
                        source_code[: sub_target.end_byte].count("\n") + 1
                    )

            if_statement_start_line = source_code[: if_statement_node.start_byte].count("\n") + 1
            if_statement_end_line = source_code[: if_statement_node.end_byte].count("\n") + 1
            line_scope = (if_statement_start_line, if_statement_end_line)
            info = (
                condition_start_line,
                condition_end_line,
                condition_str,
                (true_branch_start_line, true_branch_end_line),
                (else_branch_start_line, else_branch_end_line),
            )
            if_statements[line_scope] = info
        return if_statements
    

    @staticmethod
    def extract_meta_data_of_Python_if_statements(source_code, root_node) -> Dict[Tuple, Tuple]:
        """
        Extract meta data of if statements in Python
        TODO: Current implementation only extract the condition of if-statements
        The branch conditions of elif_clause are not handled.
        """
        if_statement_nodes = TSAnalyzer.find_nodes_by_type(root_node, "if_statement")
        if_statements = {}

        for if_statement_node in if_statement_nodes:
            sub_node_types = if_statement_node.children

            condition_str = source_code[sub_node_types[1].start_byte:sub_node_types[1].end_byte]
            condition_start_line = source_code[: sub_node_types[1].start_byte].count("\n") + 1
            condition_end_line = source_code[: sub_node_types[1].end_byte].count("\n") + 1
            true_branch_start_line = source_code[: sub_node_types[3].start_byte].count("\n") + 1
            true_branch_end_line = source_code[: sub_node_types[3].end_byte].count("\n") + 1

            if "else_clause" in [sub_node.type for sub_node in sub_node_types] or "elif_clause" in [sub_node.type for sub_node in sub_node_types]:
                else_branch_start_line = source_code[: sub_node_types[4].start_byte].count("\n") + 1
                else_branch_end_line = source_code[: if_statement_node.end_byte].count("\n") + 1
            else:
                else_branch_start_line = 0
                else_branch_end_line = 0

            if_statement_start_line = source_code[: if_statement_node.start_byte].count("\n") + 1
            if_statement_end_line = source_code[: if_statement_node.end_byte].count("\n") + 1
            line_scope = (if_statement_start_line, if_statement_end_line)
            info = (
                condition_start_line,
                condition_end_line,
                condition_str,
                (true_branch_start_line, true_branch_end_line),
                (else_branch_start_line, else_branch_end_line),
            )
            if_statements[line_scope] = info
        return if_statements
                

    def find_if_statements(self, source_code, root_node) -> Dict[Tuple, Tuple]:
        """
        Find all the if statements in the function
        :param source_code: the content of the function
        :param root_node: the root node of the parse tree
        """
        if self.ts_parser.language_setting in ["C", "C++"]:
            return self.extract_meta_data_of_C_CPP_if_statements(source_code, root_node)
        elif self.ts_parser.language_setting in ["Java"]:
            return self.extract_meta_data_of_Java_if_statements(source_code, root_node)
        elif self.ts_parser.language_setting in ["Python"]:
            return self.extract_meta_data_of_Python_if_statements(source_code, root_node)


    @staticmethod
    def extract_meta_data_of_Java_loop_statements(source_code, root_node) -> Dict[Tuple, Tuple]:
        loop_statements = {}
        for_statement_nodes = TSAnalyzer.find_nodes_by_type(root_node, "for_statement")
        for_statement_nodes.extend(TSAnalyzer.find_nodes_by_type(root_node, "enhanced_for_statement"))
        while_statement_nodes = TSAnalyzer.find_nodes_by_type(root_node, "while_statement")

        for loop_node in for_statement_nodes:
            loop_start_line = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end_line = source_code[: loop_node.end_byte].count("\n") + 1

            header_line_start = 0
            header_line_end = 0
            header_str = ""
            loop_body_start_line = 0
            loop_body_end_line = 0

            header_start_byte = 0
            header_end_byte = 0

            for loop_child_node in loop_node.children:
                if loop_child_node.type == "(":
                    header_line_start = source_code[: loop_child_node.start_byte].count("\n") + 1
                    header_start_byte = loop_child_node.end_byte
                if loop_child_node.type == ")":
                    header_line_end = source_code[: loop_child_node.end_byte].count("\n") + 1
                    header_end_byte = loop_child_node.start_byte
                    header_str = source_code[header_start_byte: header_end_byte]
                if loop_child_node.type == "block":
                    lower_lines = []
                    upper_lines = []
                    for loop_child_child_node in loop_child_node.children:
                        if loop_child_child_node.type not in {"{", "}"}:
                            lower_lines.append(source_code[: loop_child_child_node.start_byte].count("\n") + 1)
                            upper_lines.append(source_code[: loop_child_child_node.end_byte].count("\n") + 1)
                    loop_body_start_line = min(lower_lines)
                    loop_body_end_line = max(upper_lines)
                if loop_child_node.type == "expression_statement":
                    loop_body_start_line = source_code[: loop_child_node.start_byte].count("\n") + 1
                    loop_body_end_line = source_code[: loop_child_node.end_byte].count("\n") + 1
            loop_statements[(loop_start_line, loop_end_line)] = (
                header_line_start,
                header_line_end,
                header_str,
                loop_body_start_line,
                loop_body_end_line,
            )

        for loop_node in while_statement_nodes:
            loop_start_line = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end_line = source_code[: loop_node.end_byte].count("\n") + 1

            header_line_start = 0
            header_line_end = 0
            header_str = ""
            loop_body_start_line = 0
            loop_body_end_line = 0

            for loop_child_node in loop_node.children:
                if loop_child_node.type == "parenthesized_expression":
                    header_line_start = source_code[: loop_child_node.start_byte].count("\n") + 1
                    header_line_end = source_code[: loop_child_node.end_byte].count("\n") + 1
                    header_str = source_code[loop_child_node.start_byte: loop_child_node.end_byte]
                if loop_child_node.type == "block":
                    lower_lines = []
                    upper_lines = []
                    for loop_child_child_node in loop_child_node.children:
                        if loop_child_child_node.type not in {"{", "}"}:
                            lower_lines.append(source_code[: loop_child_child_node.start_byte].count("\n") + 1)
                            upper_lines.append(source_code[: loop_child_child_node.end_byte].count("\n") + 1)
                    loop_body_start_line = min(lower_lines)
                    loop_body_end_line = max(upper_lines)
            loop_statements[(loop_start_line, loop_end_line)] = (
                header_line_start,
                header_line_end,
                header_str,
                loop_body_start_line,
                loop_body_end_line,
            )
        return loop_statements


    @staticmethod
    def extract_meta_data_of_C_CPP_while_statements(source_code, root_node) -> Dict[Tuple, Tuple]:
        loop_statements = {}
        for_statement_nodes = TSAnalyzer.find_nodes_by_type(root_node, "for_statement")
        while_statement_nodes = TSAnalyzer.find_nodes_by_type(root_node, "while_statement")

        for loop_node in for_statement_nodes:
            loop_start_line = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end_line = source_code[: loop_node.end_byte].count("\n") + 1

            header_line_start = 0
            header_line_end = 0
            header_str = ""
            loop_body_start_line = 0
            loop_body_end_line = 0

            header_start_byte = 0
            header_end_byte = 0

            for loop_child_node in loop_node.children:
                if loop_child_node.type == "(":
                    header_line_start = source_code[: loop_child_node.start_byte].count("\n") + 1
                    header_start_byte = loop_child_node.end_byte
                if loop_child_node.type == ")":
                    header_line_end = source_code[: loop_child_node.end_byte].count("\n") + 1
                    header_end_byte = loop_child_node.start_byte
                    header_str = source_code[header_start_byte: header_end_byte]
                if loop_child_node.type == "block":
                    lower_lines = []
                    upper_lines = []
                    for loop_child_child_node in loop_child_node.children:
                        if loop_child_child_node.type not in {"{", "}"}:
                            lower_lines.append(source_code[: loop_child_child_node.start_byte].count("\n") + 1)
                            upper_lines.append(source_code[: loop_child_child_node.end_byte].count("\n") + 1)
                    loop_body_start_line = min(lower_lines)
                    loop_body_end_line = max(upper_lines)
                if "statement" in loop_child_node.type:
                    loop_body_start_line = source_code[: loop_child_node.start_byte].count("\n") + 1
                    loop_body_end_line = source_code[: loop_child_node.end_byte].count("\n") + 1
            loop_statements[(loop_start_line, loop_end_line)] = (
                header_line_start,
                header_line_end,
                header_str,
                loop_body_start_line,
                loop_body_end_line,
            )

        for loop_node in while_statement_nodes:
            loop_start_line = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end_line = source_code[: loop_node.end_byte].count("\n") + 1

            header_line_start = 0
            header_line_end = 0
            header_str = ""
            loop_body_start_line = 0
            loop_body_end_line = 0

            for loop_child_node in loop_node.children:
                if loop_child_node.type == "parenthesized_expression":
                    header_line_start = source_code[: loop_child_node.start_byte].count("\n") + 1
                    header_line_end = source_code[: loop_child_node.end_byte].count("\n") + 1
                    header_str = source_code[loop_child_node.start_byte: loop_child_node.end_byte]
                if "statement" in loop_child_node.type:
                    lower_lines = []
                    upper_lines = []
                    for loop_child_child_node in loop_child_node.children:
                        if loop_child_child_node.type not in {"{", "}"}:
                            lower_lines.append(source_code[: loop_child_child_node.start_byte].count("\n") + 1)
                            upper_lines.append(source_code[: loop_child_child_node.end_byte].count("\n") + 1)
                    if len(upper_lines) == 0 or len(lower_lines) == 0:
                        continue
                    loop_body_start_line = min(lower_lines)
                    loop_body_end_line = max(upper_lines)
            loop_statements[(loop_start_line, loop_end_line)] = (
                header_line_start,
                header_line_end,
                header_str,
                loop_body_start_line,
                loop_body_end_line,
            )
        return loop_statements
    

    @staticmethod
    def extract_meta_data_of_Python_loop_statements(source_code, root_node) -> Dict[Tuple, Tuple]:
        loop_statements = {}
        loop_nodes = TSAnalyzer.find_nodes_by_type(root_node, "for_statement")
        loop_nodes.extend(TSAnalyzer.find_nodes_by_type(root_node, "while_statement"))

        for loop_node in loop_nodes:
            loop_start_line = source_code[: loop_node.start_byte].count("\n") + 1
            loop_end_line = source_code[: loop_node.end_byte].count("\n") + 1

            header_line_start = 0
            header_line_end = 0
            header_str = ""
            loop_body_start_line = 0
            loop_body_end_line = 0

            for loop_child_node in loop_node.children:
                if loop_child_node.type == ":":
                    header_line_start = source_code[: loop_node.start_byte].count("\n") + 1
                    header_line_end = source_code[: loop_child_node.start_byte].count("\n") + 1
                    header_str = source_code[loop_node.start_byte: loop_child_node.start_byte]
                if loop_child_node.type == "block":
                    loop_body_start_line = source_code[: loop_child_node.start_byte].count("\n") + 1
                    loop_body_end_line = source_code[: loop_child_node.end_byte].count("\n") + 1
                    
            loop_statements[(loop_start_line, loop_end_line)] = (
                header_line_start,
                header_line_end,
                header_str,
                loop_body_start_line,
                loop_body_end_line
            )
        return loop_statements
    

    def find_loop_statements(self, source_code, root_node) -> Dict[Tuple, Tuple]:
        """
        Find all the loop statements in the function
        :param source_code: the content of the function
        :param root_node: the root node of the parse tree
        """
        if self.ts_parser.language_setting in ["C", "C++"]:
            return self.extract_meta_data_of_C_CPP_while_statements(source_code, root_node)
        elif self.ts_parser.language_setting in ["Java"]:
            return self.extract_meta_data_of_Java_loop_statements(source_code, root_node)
        elif self.ts_parser.language_setting in ["Python"]:
            return self.extract_meta_data_of_Python_loop_statements(source_code, root_node)

    #################################################
    ########## Control Order Analysis ################
    #################################################
    @staticmethod
    def check_control_order(function: Function, src_line_number: str, sink_line_number: str) -> bool:
        """
        If the function return True, the line src_line_number may be execeted before the line sink_line_number.
        The semantics of return statements are not considered.
        This is an over-approximation of the control order.
        """
        src_line_number_in_function = src_line_number
        sink_line_number_in_function = sink_line_number

        if src_line_number_in_function == sink_line_number_in_function:
            return True

        # Consider branches, return false if src and sink in different branches
        for if_statement_start_line, if_statement_end_line in function.if_statements:
            (
                _,
                _,
                _,
                (true_branch_start_line, true_branch_end_line),
                (else_branch_start_line, else_branch_end_line),
            ) = function.if_statements[(if_statement_start_line, if_statement_end_line)]
            if (
                true_branch_start_line
                <= src_line_number_in_function
                <= true_branch_end_line
                and else_branch_start_line
                <= sink_line_number_in_function
                <= else_branch_end_line
                and else_branch_start_line != 0
                and else_branch_end_line != 0
            ):
                return False
            
        # Consider loops
        if src_line_number_in_function > sink_line_number_in_function:
            for loop_start_line, loop_end_line in function.loop_statements:
                (                
                    _,
                    _,
                    _,
                    loop_body_start_line,
                    loop_body_end_line,
                ) = function.loop_statements[(loop_start_line, loop_end_line)]
                if (
                    loop_body_start_line
                    <= src_line_number_in_function
                    <= loop_body_end_line
                    and loop_body_start_line
                    <= sink_line_number_in_function
                    <= loop_body_end_line
                ):
                    return True
            return False
        return True
    
    #######################################################
    ########## Control reachability Analysis ##############
    #######################################################
    @staticmethod
    def check_control_reachability(function: Function, src_line_number: str, sink_line_number: str) -> bool:
        """
        If the function return True, the line src_line_number may be execeted before the line sink_line_number.
        The semantics of return statements are considered.
        This is an over-approximation of the control reachability.
        """
        if TSAnalyzer.check_control_order(function, src_line_number, sink_line_number) is False:
            return False
        
        # TODO: Temporarily disable the return satement check
        # for retstmt, retstmt_line_number in function.retsmts:
        #     if TSAnalyzer.check_control_order(function, src_line_number, retstmt_line_number) and \
        #         not TSAnalyzer.check_control_order(function, sink_line_number, retstmt_line_number):
        #         return False
        return True
    
    #################################################
    ########## AST visitor utility ##################
    #################################################
    @staticmethod
    def find_all_nodes(root_node: tree_sitter.Node) -> List[tree_sitter.Node]:
        if root_node is None:
            return []
        nodes = [root_node]
        for child_node in root_node.children:
            nodes.extend(TSAnalyzer.find_all_nodes(child_node))
        return nodes

    @staticmethod
    def find_nodes_by_type(
        root_node: tree_sitter.Node, node_type: str, k=0
    ) -> List[tree_sitter.Node]:
        """
        Find all the nodes with the specific type in the parse tree
        :param root_node: the root node of the parse tree
        :param node_type: the type of the nodes to be found
        """
        nodes = []
        if k > 100:
            return []
        if root_node.type == node_type:
            nodes.append(root_node)
        for child_node in root_node.children:
            nodes.extend(TSAnalyzer.find_nodes_by_type(child_node, node_type, k+1))
        return nodes

    def find_node_by_line_number(
        self, line_number: int
    ) -> List[Tuple[str, tree_sitter.Node]]:
        """
        Find the node that contains the specific line number
        :param line_number: the line number to be searched
        """
        code_node_list = []
        for function_id in self.environment:
            function = self.environment[function_id]
            if (
                not function.start_line_number
                <= line_number
                <= function.end_line_number
            ):
                continue
            all_nodes = TSAnalyzer.find_all_nodes(function.parse_tree_root_node)
            for node in all_nodes:
                start_line = (
                    function.function_code[: node.start_byte].count("\n")
                    + function.start_line_number
                )
                end_line = (
                    function.function_code[: node.end_byte].count("\n")
                    + function.start_line_number
                )
                if start_line == end_line == line_number:
                    code_node_list.append((function.function_code, node))
        return code_node_list
    

    #################################################
    ############# Custimized Functions ##############
    #################################################

    def get_function_from_localvalue(self, value: LocalValue) ->  Function:
        """
        Get the function from the local value.
        """
        file_name = value.file
        for function_id, function in self.environment.items():
            if function.file_name == file_name:
                if function.start_line_number <= value.line_number <= function.end_line_number:
                    return function
        return None
    
    
    def get_caller_functions(self, function: Function) -> List[Function]:
        """
        Get the caller function of the function.
        """
        callee_id = function.function_id
        if callee_id not in self.callee_caller_map.keys():
            return []
        caller_ids = self.callee_caller_map[function.function_id]
        caller = [self.environment[caller_id] for caller_id in caller_ids]
        return caller
    
    
    def get_callee_functions_by_name(self, function: Function, callee:str) -> List[Function]:
        """
        Get the callee function of the function with name `callee`.
        :param function: the function to be analyzed
        :param callee: the name of the callee function
        """
        while callee in self.ts_parser.macro_map:
            callee = self.ts_parser.macro_map[callee]
        if function.function_id not in self.caller_callee_map.keys():
            return []
        callee_list = []
        for callee_id in self.caller_callee_map[function.function_id]:
            if self.environment[callee_id].function_name == callee:
                callee_list.append(self.environment[callee_id])
        return callee_list
    

    def get_parameter_by_index(self, function: Function, index: int) -> LocalValue:
        """
        Get the parameter of the function with index `index`.
        :param function: the function to be analyzed
        :param index: the index of the parameter, starting from 0
        """
        file_code = self.code_in_projects[function.file_name]
        parameters = self.find_nodes_by_type(function.parse_tree_root_node, "parameter_declaration")
        if index >= len(parameters):
            return None
        nodes = self.find_nodes_by_type(parameters[index], "identifier")
        if len(nodes) == 0:
            return None
        parameter_node = nodes[-1]
        name = file_code[parameter_node.start_byte:parameter_node.end_byte]
        line_number = file_code[:parameter_node.start_byte].count("\n") + 1
        return LocalValue(name, line_number, ValueType.PARA, function.file_name)
    

    def get_argument_by_index(self, function: Function, callee_name: str, index: int) -> List[LocalValue]:
        """
        Get the argument by callee_name and index.
        :param function: the function to be analyzed
        :param callee_name: the name of the callee function
        :param index: the index of the argument, starting from 0
        """
        result = []
        call_site_nodes = self.find_nodes_by_type(function.parse_tree_root_node, "call_expression")
        file_code = self.code_in_projects[function.file_name]
        for node in call_site_nodes:
            # use the function name as src
            is_callee = False
            for child in node.children:
                if child.type == "identifier":
                    name = file_code[child.start_byte:child.end_byte]
                    if name == callee_name:
                        is_callee = True
                    break
            if is_callee:
                for child in node.children:
                    if child.type == "argument_list" and is_callee:
                        arguments = child.children[1:-1]
                        i = 0
                        for element in arguments:
                            if element.type != ",":
                                if i == index:
                                    line_number = file_code[:element.start_byte].count("\n") + 1
                                    name = file_code[element.start_byte:element.end_byte]
                                    result.append(LocalValue(name, line_number, ValueType.ARG, function.file_name))
                                    break
                            i += 1
        return result
    

    def get_call_site_by_callee_name(self, function: Function, callee_name: str) -> List[LocalValue]:
        """
        Get the call site of the callee function with name `callee_name`.
        """
        result = []
        call_site_nodes = self.find_nodes_by_type(function.parse_tree_root_node, "call_expression")
        file_code = self.code_in_projects[function.file_name]
        for node in call_site_nodes:
            # use the function name as src
            for child in node.children:
                if child.type == "identifier":
                    name = file_code[child.start_byte:child.end_byte]
                    if name == callee_name:
                        line_number = file_code[:node.start_byte].count("\n") + 1
                        # use call site as src
                        name = file_code[node.start_byte:node.end_byte]
                        result.append(LocalValue(name, line_number, ValueType.RET, function.file_name))
        return result


    def get_name_by_line_number(self, line_number: int, file_name: str) -> str:
        """
        Get the content at `line_number` in `file`.
        """
        if file_name not in self.code_in_projects:
            return ""
        file_code = self.code_in_projects[file_name]
        file_lines = file_code.split("\n")
        if line_number > len(file_lines):
            return ""
        return file_lines[line_number - 1]


    def extract_global_variables(self, function: Function) -> List[LocalValue]:
        """
        Extract global variables in function
        """
        file_code = self.code_in_projects[function.file_name]
        defined_variables = []
        parameters = self.find_nodes_by_type(function.parse_tree_root_node, "parameter_declaration")
        for parameter in parameters:
            nodes = self.find_nodes_by_type(parameter, "identifier")
            for node in nodes:
                name = file_code[node.start_byte:node.end_byte]
                defined_variables.append(name)
        
        declearations = self.find_nodes_by_type(function.parse_tree_root_node, "declaration")
        for declearation in declearations:
            nodes = self.find_nodes_by_type(declearation, "identifier")
            for node in nodes:
                name = file_code[node.start_byte:node.end_byte]
                defined_variables.append(name)
        
        left_variables = []
        assignments = self.find_nodes_by_type(function.parse_tree_root_node, "assignment_expression")
        for assignment in assignments:
            left_value = assignment.children[0]
            nodes = self.find_nodes_by_type(left_value, "identifier")
            for node in nodes:
                name = file_code[node.start_byte:node.end_byte]
                left_variables.append(name)
        
        global_variables = []
        for variable in left_variables:
            if variable not in defined_variables:
                line_number = file_code[:node.start_byte].count("\n") + 1
                global_variables.append(LocalValue(variable, line_number, ValueType.GLOBAL, function.file_name))
        return global_variables
                

    def extract_key_points(self, function:Function, bug_type:str) -> List[LocalValue]:
        """
        Extract key points from the function, including return site, invocation site and bug related site:
        Memory leak: memory
        Null pointer dereference: deference site
        """
        source_code = function.code_without_comments
        tree = self.ts_parser.parser.parse(bytes(source_code, "utf8"))
        root = tree.root_node
        nodes = self.find_nodes_by_type(root, "return_statement")
        nodes.extend(self.find_nodes_by_type(root, "call_expression"))
        nodes.extend(self.find_nodes_by_type(root, "method_invocation"))
        nodes.extend(self.find_nodes_by_type(root, "parameter_declaration"))
        lines = []
        if bug_type == "ML":
            nodes.extend(self.find_nodes_by_type(root, "delete_expression"))
            for node in nodes:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte : node.end_byte]
                lines.append(LocalValue(name, line_number, ValueType.SINK, function.file_name))
        if bug_type == "NPD":
            nodes.extend(self.find_nodes_by_type(root, "pointer_expression"))
            nodes.extend(self.find_nodes_by_type(root, "field_expression"))
            nodes.extend(self.find_nodes_by_type(root, "subscript_expression"))
            for node in nodes:
                if node.type == "pointer_expression" and node.children[0].type != "*":
                    continue
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte : node.end_byte]
                lines.append(LocalValue(name, line_number, ValueType.SINK, function.file_name))
        if bug_type == "UAF":
            nodes.extend(self.find_nodes_by_type(root, "pointer_expression"))
            nodes.extend(self.find_nodes_by_type(root, "field_expression"))
            nodes.extend(self.find_nodes_by_type(root, "delete_expression"))
            for node in nodes:
                if node.type == "pointer_expression" and node.children[0].type != "*":
                    continue
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte : node.end_byte]
                lines.append(LocalValue(name, line_number, ValueType.SINK, function.file_name))
        lines.extend(self.extract_global_variables(function))
        return lines