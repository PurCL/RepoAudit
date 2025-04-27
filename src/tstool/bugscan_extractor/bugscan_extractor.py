import sys
import os
from os import path
from pathlib import Path
from tstool.analyzer.TS_analyzer import *
from memory.syntactic.function import *
from memory.syntactic.value import *
import tree_sitter
import json
from tqdm import tqdm
from abc import ABC, abstractmethod

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

    
class BugScanExtractor(ABC):
    """
    Extractor class providing a common interface for source/sink extraction using tree-sitter.
    """
    def __init__(
        self,
        ts_analyzer: TSAnalyzer
    ):
        self.ts_analyzer = ts_analyzer
        self.seeds: List[Tuple[Value, bool]] = []
        return
        
    def extract_all(self) -> None:
        """
        Start the seed extraction process.
        """
        pbar = tqdm(total=len(self.ts_analyzer.function_env), desc="Extracting seeds")
        for function_id in self.ts_analyzer.function_env:
            pbar.update(1)
            function: Function = self.ts_analyzer.function_env[function_id]
            if 'test' in function.file_path or 'example' in function.file_path:
                continue
            self.seeds.extend(self.find_seeds(function))
        return self.seeds
    
    @abstractmethod
    def find_seeds(self, function: Function) -> List[Tuple[Value, bool]]:
        """
        Extract the seeds that can cause the bugs from the source code.
        :param function: Function object.
        :return: A list of seed-bool pairs, indicating the seed values and the direction of the data flow.
        """
        pass


    def seed_to_str(self, seed: Tuple[Value, bool]) -> str:
        """
        dump the seed to string. 1 for forward, 0 for backward.
        """
        return str(seed[0]) + " " + str(int(seed[1]))

