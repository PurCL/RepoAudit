import sys
from os import path
from tstool.analyzer.TS_analyzer import *
from memory.syntactic.function import *
from memory.syntactic.value import *
from tqdm import tqdm
from abc import ABC, abstractmethod

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))


class DFBScanExtractor(ABC):
    """
    Extractor class providing a common interface for source/sink extraction using tree-sitter.
    """

    def __init__(self, ts_analyzer: TSAnalyzer):
        self.ts_analyzer = ts_analyzer
        self.sources: List[Value] = []
        self.sinks: List[Value] = []
        return

    def extract_all(self) -> Tuple[List[Value], List[Value]]:
        """
        Start the source/sink extraction process.
        """
        pbar = tqdm(total=len(self.ts_analyzer.function_env), desc="Parsing files")
        for function_id in self.ts_analyzer.function_env:
            pbar.update(1)
            function: Function = self.ts_analyzer.function_env[function_id]
            if "test" in function.file_path or "example" in function.file_path:
                continue
            file_content = self.ts_analyzer.code_in_files[function.file_path]
            function_root_node = function.parse_tree_root_node
            self.sources.extend(self.extract_sources(function))
            self.sinks.extend(self.extract_sinks(function))
        
        return self.sources, self.sinks

    @abstractmethod
    def extract_sources(self, function: Function) -> List[Value]:
        """
        Extract the source values that can cause the bugs from the source code.
        :param function: Function object.
        :return: A list of the sources in the ast tree of which the root is root_node.
        """
        pass

    @abstractmethod
    def extract_sinks(self, function: Function) -> List[Value]:
        """
        Extract the sink values that can cause the bugs from the source code.
        :param function: Function object.
        :return: A list of the sinks in the ast tree of which the root is root_node.
        """
        pass
