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

class IntraDetectorInput(LLMToolInput):
    def __init__(self, buggy_construct_str: str, single_function_str: str) -> None:
        """
        :param buggy_construct_str: the string indicating the buggy construct
        :param single_function_str: the string indicating the single function
        """
        self.buggy_construct_str = buggy_construct_str
        self.single_function_str = single_function_str
        return

    def __hash__(self) -> int:
        return hash((self.buggy_construct_str, self.single_function_str))
        

class IntraDetectorOutput(LLMToolOutput):
    def __init__(self, is_buggy: bool, poc_str: str) -> None:
        """
        :param is_buggy: whether the construct is buggy. The construct can be a specific expression
        :param poc_str: the string explaining the proof of concept
        """
        self.is_buggy = is_buggy
        self.poc_str = poc_str
        return


class IntraDetector(LLMTool):
    def __init__(self, bug_type: str, model_name: str, temperature: float, language: str, max_query_num: int) -> None:
        """
        :param bug_type: the type of bug to detect
        :param model_name: the model name
        :param temperature: the temperature
        :param language: the programming language
        :param max_query_num: the maximum number of queries if the model fails
        """
        super().__init__(model_name, temperature, language, max_query_num)
        self.bug_type = bug_type
        self.inline_prompt_file = f"{BASE_PATH}/prompt/{language}/{language}_{bug_type}_prompt.json"
        return

    def _get_prompt(self, input: IntraDetectorInput) -> str:
        """
        :param input: the input of intra-procedural detector
        :return: the prompt string
        """
        with open(self.inline_prompt_file, "r") as f:
            prompt_template_dict = json.load(f)
        prompt = prompt_template_dict["task"]
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_rules"])
        prompt += "\n" + "".join(prompt_template_dict["meta_prompts"])
        prompt = prompt.replace("<ANSWER>", "\n".join(prompt_template_dict["answer_format"]))
        prompt = prompt.replace("<QUESTION>", prompt_template_dict["question_template"])
        prompt = prompt.replace("<FUNCTION>", input.single_function_str)
        prompt = prompt.replace("<SEED_NAME>", input.buggy_construct_str)
        return prompt

    def _parse_response(self, response: str, input: IntraDetectorInput) -> IntraDetectorOutput:
        """
        :param response: the string response from the model
        :return: the output of intra-procedural detector
        """
        answer_match = re.search(r'Answer:\s*(\w+)', response)
        poc_match = re.search(r'PoC:\s*(.*)', response, re.DOTALL)

        if answer_match:
            answer = answer_match.group(1).strip()
            poc = poc_match.group(1).strip() if poc_match else ""
            output = IntraDetectorOutput(answer == "Yes", poc)
        else:
            print(f"Answer not found in output")
            output = None
        return output
