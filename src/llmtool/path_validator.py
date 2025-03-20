from os import path
import json
import time
from typing import List, Set, Optional, Dict
from .LLM_utils import *
from .LLM_tool import *
from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.syntactic.api import *
BASE_PATH = Path(__file__).resolve().parents[1]

class PathValidatorInput(LLMToolInput):
    def __init__(self, values: List[Value], values_to_functions: Dict[Value, Function]) -> None:
        self.values = values
        self.values_to_functions = values_to_functions
        return

    def __hash__(self) -> int:
        return hash(str([str(value) for value in self.values]))
        

class PathValidatorOutput(LLMToolOutput):
    def __init__(self, is_reachable: bool, poc_str: str) -> None:
        self.is_reachable = is_reachable
        self.poc_str = poc_str   
        return


class PathValidator(LLMTool):
    def __init__(self, model_name: str, temperature: float, language: str, max_query_num: int) -> None:
        """
        :param model_name: the model name
        :param temperature: the temperature
        :param language: the programming language
        :param max_query_num: the maximum number of queries if the model fails
        """
        super().__init__(model_name, temperature, language, max_query_num)
        self.path_valid_prompt_file = f"{BASE_PATH}/prompt/llmtool/{language}/{language}_path_valid_prompt.json"
        return

    def _get_prompt(self, input: PathValidatorInput) -> str:
        with open(self.dfa_prompt_file, "r") as f:
            prompt_template_dict = json.load(f)
        prompt = prompt_template_dict["task"]
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_rules"])
        prompt += "\n" + "".join(prompt_template_dict["meta_prompts"])
        prompt = prompt.replace("<ANSWER>", "\n".join(prompt_template_dict["answer_format"]))
        prompt = prompt.replace("<QUESTION>", prompt_template_dict["question_template"])
        # TODO
        return prompt

    def _parse_response(self, response: str) -> PathValidatorOutput:
        answer_match = re.search(r'Answer:\s*(\w+)', response)
        poc_match = re.search(r'PoC:\s*(.*)', response, re.DOTALL)

        if answer_match:
            answer = answer_match.group(1).strip()
            poc = poc_match.group(1).strip() if poc_match else ""
            output = PathValidatorOutput(answer == "Yes", poc)
        else:
            print(f"Answer not found in output")
            output = None
        return output
