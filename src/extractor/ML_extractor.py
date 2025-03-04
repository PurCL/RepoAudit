from parser.base_parser import *
from parser.C_parser import *
from parser.go_parser import *
from extractor.util import *
import tree_sitter
import argparse
import os
import json
from tqdm import tqdm

class ML_Extractor:
    def __init__(
        self,
        project_path: str,
        language_setting: str,
        sample_src: bool,
        src_functions,
        sink_functions,
        src_path: str,
        sink_path: str
    ):
        cwd = Path(__file__).resolve().parent.absolute()
        TSPATH = cwd / "../../lib/build/"
        language_path = TSPATH / "my-languages.so"

        self.project_path = project_path
        self.suffix = set()
        self.all_files = {}
        self.sample_src = sample_src
        self.src_functions = src_functions
        self.sink_functions = sink_functions

        if language_setting == "C":
            self.language = tree_sitter.Language(str(language_path), "c")
            self.suffix = {"c", "h"}
        elif language_setting == "C++":
            self.language = tree_sitter.Language(str(language_path), "cpp")
            self.suffix = {"cpp", "cc", "hpp", "h", "c"}
        else:
            raise ValueError("Invalid language setting")
        
        self.parser = tree_sitter.Parser()
        self.parser.set_language(self.language)
        self.travese_files(project_path, self.suffix)
        self.src_path = src_path
        self.sink_path = sink_path


    def run(self):
        """
        Start the extraction process.
        """
        src_lines = []
        sink_lines = []

        pbar = tqdm(total=len(self.all_files), desc="Parsing files")
        for file_name, file_code in self.all_files.items():
            pbar.update(1)
            if 'test' in file_name or 'example' in file_name:
                continue
            tree = self.parser.parse(bytes(file_code, "utf8"))
            root = tree.root_node
            if self.src_functions:
                src_lines.extend(find_invocation_sites(file_code, root, set(self.src_functions), file=file_name))
            else:
                src_lines.extend(self.find_ml_src(file_code, root, file=file_name))
            if self.sink_functions:
                sink_lines.extend(find_invocation_sites(file_code, root, set(self.src_functions), file=file_name))
            sink_lines.extend(self.find_ml_sink(file_code, root, file=file_name))
            
            if self.sample_src:
                dict_src = {}
                for src_line in src_lines:
                    key = src_line.name + src_line.file
                    if key not in dict_src:
                        dict_src[key] = src_line
                src_lines = list(dict_src.values())

        with open(self.src_path, 'w') as f:
            json.dump([str(src_line) for src_line in src_lines], f, indent=4, sort_keys=True)
        with open(self.sink_path, 'w') as f:
            json.dump([str(sink_line) for sink_line in sink_lines], f, indent=4, sort_keys=True)
        return


    def travese_files(self, project_path: str, suffix: set) -> None:
        """
        Traverse all files in the project path.
        """
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file.split(".")[-1] not in suffix:
                    continue
                with open(os.path.join(root, file), "r") as c_file:
                    c_file_content = c_file.read()
                    self.all_files[os.path.join(root, file)] = c_file_content
            for dir in dirs:
                self.travese_files(os.path.join(root, dir), suffix)


    @staticmethod
    def find_ml_src(source_code: str, root_node: tree_sitter.Node, file: str="") -> List[LocalValue]:
        """
        Extract the Memory Leak source from the source code.
        1. malloc, realloc, calloc
        2. strdup, strndup
        3. asprintf, vasprintf
        4. new
        5. getline
        """
        nodes = find_nodes_by_type(root_node, "call_expression")
        nodes.extend(find_nodes_by_type(root_node, "new_expression"))

        lines = []
        for node in nodes:
            is_src_node = False
            if node.type == "new_expression":
                is_src_node = True
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name in ("malloc", "calloc", "realloc", "strdup", "strndup", "asprintf", "vasprintf", "getline"):
                            is_src_node = True

            if is_src_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code.split("\n")[line_number - 1]
                lines.append(LocalValue(name, line_number, ValueType.SRC, file=file))
        return lines     
    

    @staticmethod
    def find_ml_sink(source_code: str, root_node: tree_sitter.Node, file: str="") -> List[LocalValue]:
        """
        Extract the Memory Leak sink from the source code.
        1. free
        2. delete
        """
        nodes = find_nodes_by_type(root_node, "call_expression")
        nodes.extend(find_nodes_by_type(root_node, "delete_expression"))

        lines = []
        for node in nodes:
            is_sink_node = False
            if node.type == "delete_expression":
                is_sink_node = True
            if node.type == "call_expression":
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        if name == "free":
                            is_sink_node = True

            if is_sink_node:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code.split("\n")[line_number - 1]
                lines.append(LocalValue(name, line_number, ValueType.SINK, file=file))
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
            "C",
            "C++",
        ],
        help="Specify the language",
    )
    parser.add_argument(
        "--src-path",
        type=str,
        help="Specify the source path",
    )
    parser.add_argument(
        "--sink-path",
        type=str,
        help="Specify the sink path",
    )
    parser.add_argument(
        "--sample-src",
        action="store_true",
        help="sample the sources if set",
    )
    parser.add_argument(
        "--src-functions",
        nargs='*',
        help="Specify the source functions",
    )
    parser.add_argument(
        "--sink-functions",
        nargs='*',
        help="Specify the sink functions",
    )
    args = parser.parse_args()
    project_path = args.project_path
    language_setting = args.language
    sample_src = args.sample_src
    src_functions = args.src_functions
    sink_functions = args.sink_functions
    src_path = args.src_path
    sink_path = args.sink_path
    
    ml_extractor = ML_Extractor(project_path, language_setting, sample_src, src_functions, sink_functions, src_path, sink_path) 
    ml_extractor.run()


if __name__ == "__main__":
    start_extract()