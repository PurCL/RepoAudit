from os import path
import json
import time
from typing import List, Set, Optional, Dict
from llmtool.LLM_utils import *
from llmtool.LLM_tool import *
from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.syntactic.api import *
BASE_PATH = Path(__file__).resolve().parent.parent.parent

class DebugSliceAnalyzerInput(LLMToolInput):
    def __init__(self, err_message: str, debug_seed: Value, debug_slice: str, request_str: str) -> None:
        """
        :param err_message: the crash message
        :param debug_seed: the debug seed
        :param debug_slice: the debug slice
        :param request_str: the request string
        """
        self.err_message = err_message
        self.debug_seed = debug_seed
        self.debug_slice = debug_slice
        self.request_str = request_str
        return

    def __hash__(self) -> int:
        return hash((self.err_message, str(self.debug_seed), self.debug_slice, self.request_str))
        

class DebugSliceAnalyzerOutput(LLMToolOutput):
    def __init__(self, explanation_str: str) -> None:
        """
        :param explanation_str: the string explaining the targeted runtime error
        """
        self.explanation_str = explanation_str
        return
    
    def __str__(self):
        return f"Explanation: {self.explanation_str}"


class DebugSliceAnalyzer(LLMTool):
    def __init__(self, model_name: str, temperature: float, language: str, max_query_num: int, logger: Logger) -> None:
        """
        :param model_name: the model name
        :param temperature: the temperature
        :param language: the programming language
        :param max_query_num: the maximum number of queries if the model fails
        :param logger: the logger
        """
        super().__init__(model_name, temperature, language, max_query_num, logger)
        self.prompt_file = f"{BASE_PATH}/prompt/{language}/debugscan/debug_slice_analyzer.json"
        return

    def _get_prompt(self, input: DebugSliceAnalyzerInput) -> str:
        """
        :param input: the input of intra-procedural detector
        :return: the prompt string
        """
        with open(self.prompt_file, "r") as f:
            prompt_template_dict = json.load(f)
        prompt = prompt_template_dict["task"]
        prompt += "\n" + "".join(prompt_template_dict["meta_prompts"])
        prompt = prompt.replace("<ANSWER>", "\n".join(prompt_template_dict["answer_format"]))
        prompt = prompt.replace("<FUNCTION>", str(input.debug_slice))
        prompt = prompt.replace("<ERR_MESSAGE>", input.err_message)
        prompt = prompt.replace("<DEBUG_REQUEST>", input.request_str)
        return prompt

    def _parse_response(self, response: str, input: DebugSliceAnalyzerInput) -> DebugSliceAnalyzerOutput:
        """
        :param input: the input of the model
        :return: the output of the tool
        """
        return DebugSliceAnalyzerOutput(response)
