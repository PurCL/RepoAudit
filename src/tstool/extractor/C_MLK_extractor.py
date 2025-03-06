from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.C_TS_analyzer import *
import tree_sitter
import argparse
import os
import json
from tqdm import tqdm

class MLK_Extractor:
    def __init__(
        self,
        project_path: str,
        language_setting: str,
        src_functions,
        src_path: str,
    ):
        cwd = Path(__file__).resolve().parent.absolute()
        TSPATH = cwd / "../../../lib/build/"
        language_path = TSPATH / "my-languages.so"

        self.project_path = project_path
        self.suffix = set()
        self.all_files = {}
        self.src_functions = src_functions

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

    def run(self):
        """
        Start the extraction process.
        """
        src_lines = []

        pbar = tqdm(total=len(self.all_files), desc="Parsing files")
        for file_name, file_code in self.all_files.items():
            pbar.update(1)
            if 'test' in file_name or 'example' in file_name.lower():
                continue
            tree = self.parser.parse(bytes(file_code, "utf8"))
            root = tree.root_node
            src_lines.extend(self.find_mlk_src(file_code, root, file=file_name))

        with open(self.src_path, 'w') as f:
            json.dump([str(src_line) for src_line in src_lines], f, indent=4, sort_keys=True)


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
    def find_mlk_src(source_code: str, root_node: tree_sitter.Node, file: str="") -> List[LocalValue]:
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
                name = source_code.split("\n")[line_number - 1].strip()
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
        "--src-functions",
        nargs='*',
        help="Specify the source functions",
    )
    args = parser.parse_args()
    project_path = args.project_path
    language_setting = args.language
    src_functions = args.src_functions
    src_path = args.src_path
    
    mlk_extractor = MLK_Extractor(project_path, language_setting, src_functions, src_path) 
    mlk_extractor.run()


if __name__ == "__main__":
    start_extract()