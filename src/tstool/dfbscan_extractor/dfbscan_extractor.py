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
        pbar = tqdm(
            total=len(self.ts_analyzer.function_env)
            + len(self.ts_analyzer.globals_env),
            desc="Parsing files",
        )
        for function_id in self.ts_analyzer.function_env:
            pbar.update(1)
            function: Function = self.ts_analyzer.function_env[function_id]
            if "test" in function.file_path or "example" in function.file_path:
                continue
            file_content = self.ts_analyzer.code_in_files[function.file_path]
            function_root_node = function.parse_tree_root_node
            self.sources.extend(self.extract_sources(function))
            self.sinks.extend(self.extract_sinks(function))

        for global_id, global_var in self.ts_analyzer.globals_env.items():
            pbar.update(1)
            node = self.ts_analyzer.globalsRawDataDic[global_id][2]
            if self.is_global_source(node):
                global_var.label = ValueLabel.SRC
                self.sources.append(global_var)

            if self.is_global_sink(node):
                global_var.label = ValueLabel.SINK
                self.sinks.append(global_var)

        pbar.close()

        return self.sources, self.sinks

    @abstractmethod
    def is_global_source(self, global_var: Tree) -> bool:
        pass

    @abstractmethod
    def is_global_sink(self, global_var: Tree) -> bool:
        pass

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
