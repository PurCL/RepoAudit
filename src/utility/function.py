import tree_sitter

class Function:
    def __init__(
        self,
        function_id: int,
        function_name: str,
        function_code: str,
        start_line_number: int,
        end_line_number: int,
        function_node: tree_sitter.Node,
        file_name: str
    ) -> None:
        """
        Record basic facts of the function
        """
        self.function_id = function_id
        self.function_name = function_name
        self.function_code = function_code
        self.start_line_number = start_line_number
        self.end_line_number = end_line_number
        self.file_name = file_name

        self.code_without_comments = ""
        self.lined_code_without_comments = ""

        # Attention: the parse tree is in the context of the whole file
        self.parse_tree_root_node = function_node  # root node of the parse tree of the current function
        self.call_site_nodes = []   # call site info

        ## Results of AST node type analysis
        self.paras = set([])        # A set of (Expr, int) tuples, where int indicates the index of the parameter
        self.retsmts = []           # A list of (Node, int) tuples, where int indicates the AST node of the return statement and its line number

        ## Results of intraprocedural control flow analysis
        self.if_statements = {}     # if statement info
        self.loop_statements = {}   # loop statement info


    def file_line2function_line(self, file_line: int) -> int:
        return file_line - self.start_line_number + 1