import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
from parser.program_parser import *

class TSFunctionProcessor:
    """
    FunctionProcessor class for removing comments in the function and attaching the line numbers
    """

    def __init__(self, ts_analyzer, language) -> None:
        self.ts_analyzer = ts_analyzer
        self.language = language

        self.source_code = ""
        self.lined_code = ""
        return

    def transform(self, source_code):
        self.source_code = source_code
        self.attach_line_number()
        return

    def attach_line_number(self):
        self.lined_code = ""
        function_content = "1. " + self.source_code
        line_no = 2
        for ch in function_content:
            if ch == "\n":
                self.lined_code += "\n" + str(line_no) + ". "
                line_no += 1
            else:
                self.lined_code += ch
        return
