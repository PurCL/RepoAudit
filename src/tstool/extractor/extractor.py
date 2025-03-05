import sys
import os
from os import path
from pathlib import Path
from tstool.analyzer.TS_analyzer import *
from memory.function import *
from memory.localvalue import *
from typing import List, Tuple, Dict, Set
import tree_sitter
import json
from tree_sitter import Language
from tqdm import tqdm
import networkx as nx
from abc import ABC, abstractmethod

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

    
class Extractor(ABC):
    """
    Extractor class providing a common interface for source/sink extraction using tree-sitter.
    """
    def __init__(
        self,
        project_path: str,
        language_setting: str,
        seed_path: str
    ):
        cwd = Path(__file__).resolve().parent.absolute()
        TSPATH = cwd / "../../../lib/build/"
        language_path = TSPATH / "my-languages.so"

        self.project_path = project_path
        self.suffix = set()
        self.all_files = {}

        if language_setting == "C":
            self.language = tree_sitter.Language(str(language_path), "c")
            self.suffix = {"c", "h"}
        elif language_setting == "C++":
            self.language = tree_sitter.Language(str(language_path), "cpp")
            self.suffix = {"cpp", "cc", "hpp", "h", "c"}
        elif language_setting == "Go":
            self.language = tree_sitter.Language(str(language_path), "go")
            self.suffix = {"go"}
        else:
            raise ValueError("Invalid language setting")
        
        self.parser = tree_sitter.Parser()
        self.parser.set_language(self.language)
        self.seed_path = seed_path
        self.travese_files(project_path, self.suffix)
        

    def run(self):
        """
        Start the seed extraction process.
        """
        seed_lines = []

        pbar = tqdm(total=len(self.all_files), desc="Parsing files")
        for file_name, file_code in self.all_files.items():
            pbar.update(1)
            if 'test' in file_name or 'example' in file_name:
                continue
            tree = self.parser.parse(bytes(file_code, "utf8"))
            root = tree.root_node

            nodes = find_nodes_by_type(root, "return_statement")
            for node in nodes:
                for sub_node in node.children:
                    print(sub_node.type)
                    print(file_code[sub_node.start_byte:sub_node.end_byte])
                    print("=====================================")

            seed_lines.extend(self.find_seed(file_code, root, file=file_name))
    
        with open(self.seed_path, 'w') as f:
            json.dump([str(seed_line) for seed_line in seed_lines], f, indent=4, sort_keys=True)
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

    
    @abstractmethod
    def find_seed(self, source_code: str, root_node: tree_sitter.Node, file: str) -> List[LocalValue]:
        """
        Extract the seeds that can cause the bugs from the source code.
        :param source_code: Content of the source file.
        :param tree: Parsed syntax tree.
        :param file_path: Path of the source file.
        """
        pass
