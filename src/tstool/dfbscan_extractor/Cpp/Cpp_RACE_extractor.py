from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from ..dfbscan_extractor import *


class Cpp_Race_Extractor(DFBScanExtractor):
    def extract_sources(self, function: Function) -> List[Value]:
        """
        Extract potential shared resources or thread creation points as sources.
        1. Global variables (shared across threads).
        2. Static variables (shared across function calls/threads).
        3. Arguments passed to thread creation functions (std::thread, pthread_create).
        """
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path
        
        sources = []

        # 1. Find global variables (defined at the top level of the file)
        # Note: function.parse_tree_root_node is usually the function body.
        # To find global variables, we need to access the root node of the file's AST.
        # However, the current architecture passes a 'Function' object.
        # We will try to parse the whole file content to find global variables if possible,
        # or rely on the fact that TSAnalyzer might have parsed the whole file.
        
        # Re-parsing the file to find global declarations
        parser = Parser()
        parser.set_language(self.ts_analyzer.language)
        tree = parser.parse(bytes(source_code, "utf8"))
        file_root_node = tree.root_node

        declarations = find_nodes_by_type(file_root_node, "declaration")
        for decl in declarations:
            # Check if the declaration is at the top level (parent is translation_unit)
            if decl.parent.type == "translation_unit":
                init_declarators = find_nodes_by_type(decl, "init_declarator")
                for init_decl in init_declarators:
                    declarator = init_decl.child_by_field_name("declarator")
                    while declarator.type in ["pointer_declarator", "reference_declarator"]:
                        declarator = declarator.child_by_field_name("declarator")
                    
                    if declarator and declarator.type == "identifier":
                        name = source_code[declarator.start_byte:declarator.end_byte]
                        line_number = source_code[:declarator.start_byte].count("\n") + 1
                        sources.append(Value(name, line_number, ValueLabel.SRC, file_path))

        # 2. Find static variables within the function
        func_declarations = find_nodes_by_type(root_node, "declaration")
        for decl in func_declarations:
            is_static = False
            for child in decl.children:
                if child.type == "storage_class_specifier" and source_code[child.start_byte:child.end_byte] == "static":
                    is_static = True
                    break
            
            if is_static:
                init_declarators = find_nodes_by_type(decl, "init_declarator")
                for init_decl in init_declarators:
                    declarator = init_decl.child_by_field_name("declarator")
                    while declarator.type in ["pointer_declarator", "reference_declarator"]:
                        declarator = declarator.child_by_field_name("declarator")
                        
                    if declarator and declarator.type == "identifier":
                        name = source_code[declarator.start_byte:declarator.end_byte]
                        line_number = source_code[:declarator.start_byte].count("\n") + 1
                        sources.append(Value(name, line_number, ValueLabel.SRC, file_path))

        # 3. Find arguments to thread creation
        call_expressions = find_nodes_by_type(root_node, "call_expression")
        for call in call_expressions:
            func_node = call.child_by_field_name("function")
            if func_node:
                func_name = source_code[func_node.start_byte:func_node.end_byte]
                if "thread" in func_name or "async" in func_name or "pthread_create" in func_name: 
                    args = call.child_by_field_name("arguments")
                    if args:
                        for arg in args.children:
                            if arg.type == "identifier":
                                name = source_code[arg.start_byte:arg.end_byte]
                                line_number = source_code[:arg.start_byte].count("\n") + 1
                                sources.append(Value(name, line_number, ValueLabel.SRC, file_path))
                            elif arg.type == "reference_expression": # std::ref(x)
                                for child in arg.children:
                                    if child.type == "identifier":
                                        name = source_code[child.start_byte:child.end_byte]
                                        line_number = source_code[:child.start_byte].count("\n") + 1
                                        sources.append(Value(name, line_number, ValueLabel.SRC, file_path))
                            elif arg.type == "unary_expression": # &x
                                for child in arg.children:
                                    if child.type == "identifier":
                                        name = source_code[child.start_byte:child.end_byte]
                                        line_number = source_code[:child.start_byte].count("\n") + 1
                                        sources.append(Value(name, line_number, ValueLabel.SRC, file_path))
        
        return sources

    def extract_sinks(self, function: Function) -> List[Value]:
        """
        Extract potential sinks for Race Condition.
        We consider ANY access (Read or Write) to a variable as a potential sink.
        This allows the LLM to detect Read-Write races.
        """
        root_node = function.parse_tree_root_node
        source_code = self.ts_analyzer.code_in_files[function.file_path]
        file_path = function.file_path
        
        sinks = []
        
        # Extract all identifiers that are used in expressions
        # This is a broad extraction, but necessary to catch reads.
        # We filter out function calls and declarations to focus on variable usage.
        
        identifiers = find_nodes_by_type(root_node, "identifier")
        for ident in identifiers:
            # Filter out declarations (we only want usage)
            parent = ident.parent
            if parent.type in ["function_declarator", "init_declarator", "declaration", "parameter_declaration"]:
                continue
            
            # Filter out function calls (the function name itself)
            if parent.type == "call_expression" and parent.child_by_field_name("function") == ident:
                continue
                
            # Filter out field access (member variables) - simplistic handling
            # if parent.type == "field_expression" and parent.child_by_field_name("field") == ident:
            #    continue

            name = source_code[ident.start_byte:ident.end_byte]
            line_number = source_code[:ident.start_byte].count("\n") + 1
            sinks.append(Value(name, line_number, ValueLabel.SINK, file_path))

        return sinks
