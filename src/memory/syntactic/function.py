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
        file_path: str,
    ) -> None:
        """
        Record basic facts of the function.
        Here, the function indicates a user-defined function or method.
        The implementation is provided in the project.
        """
        self.function_id = function_id
        self.function_name = function_name
        self.function_code = function_code
        self.start_line_number = start_line_number
        self.end_line_number = end_line_number
        self.file_path = file_path
        self.lined_code = (
            self.attach_relative_line_number()
        )  # code with line number attached

        # Attention: the parse tree is in the context of the whole file
        self.parse_tree_root_node = (
            function_node  # root node of the parse tree of the current function
        )
        self.function_call_site_nodes = []  # call site info of user-defined functions
        self.api_call_site_nodes = []  # call site info of library APIs

        ## Results of AST node type analysis
        self.paras = None  # A set of parameters
        self.retvals = None  # A set of returned values

        ## Results of intraprocedural control flow analysis
        self.if_statements = {}  # if statement info
        self.loop_statements = {}  # loop statement info

    def __hash__(self) -> int:
        return hash(
            (
                self.function_name,
                self.function_code,
                self.file_path,
                self.start_line_number,
                self.end_line_number,
            )
        )

    def file_line2function_line(self, file_line: int) -> int:
        """
        Convert the line number in the file to the line number in the function
        """
        return file_line - self.start_line_number + 1

    def attach_relative_line_number(self) -> str:
        """
        Attach line numbers to the function code.
        Line numbers start from 1.
        """
        lined_code = ""
        function_content = "1. " + self.function_code
        line_no = 2
        for ch in function_content:
            if ch == "\n":
                lined_code += "\n" + str(line_no) + ". "
                line_no += 1
            else:
                lined_code += ch
        return lined_code

    def attach_absolute_line_number(self) -> str:
        """
        Attach line numbers to the function code
        Line numbers start from self.start_line_number
        """
        lined_code = ""
        function_content = str(self.start_line_number) + ". " + self.function_code
        line_no = self.start_line_number + 1
        for ch in function_content:
            if ch == "\n":
                lined_code += "\n" + str(line_no) + ". "
                line_no += 1
            else:
                lined_code += ch
        return lined_code
