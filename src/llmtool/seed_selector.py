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

class SeedSelectorInput(LLMToolInput):
    def __init__(self, seed_function: Function, seed_list: List[Value]) -> None:
        """
        :param function: the function to be analyzed
        :param seed_set: the set of seed values
        """
        self.seed_function = seed_function
        self.seed_list = seed_list
        return
    
    def __hash__(self) -> int:
        return hash((str(self.seed_list), self.seed_function.function_id))


class SeedSelectorOutput(LLMToolOutput):
    def __init__(self, seed_list: List[Value]) -> None:
        self.seed_list = seed_list
        return
    
    def __str__(self):
        output_str = ""
        for seed in self.seed_list:
            output_str += f"- {seed}\n"
        return output_str

class SeedSelector(LLMTool):
    def __init__(self, model_name: str, temperature: float, language: str, bug_type: str, max_query_num: int) -> None:
        super().__init__(model_name, temperature, language, max_query_num)
        self.bug_type = bug_type
        self.seed_selector_prompt_file = f"{BASE_PATH}/prompt/{language}/{language}_{bug_type}_seed_selector_prompt.json"
        return

    def _get_prompt(self, input: SeedSelectorInput) -> str:
        with open(self.seed_selector_prompt_file, "r") as f:
            prompt_template_dict = json.load(f)

        prompt = prompt_template_dict["task"]
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_rules"])
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_examples"])
        prompt += "\n" + "\n".join(prompt_template_dict["meta_prompts"])

        lines_str = [", ".join(list(set([str(value.line_number - input.seed_function.start_line_number + 1) for value in input.seed_list])))]
        prompt = prompt.replace("<LINE_NUMBERS>", "\n".join(lines_str))
        prompt = prompt.replace("<FUNCTION>", input.seed_function.lined_code)
        prompt = prompt.replace("<QUESTION>", prompt_template_dict["question_template"])
        prompt = prompt.replace("<ANSWER>", "\n".join(prompt_template_dict["answer_format"]))
        return prompt

    def _parse_response(self, response: str, input: SeedSelectorInput) -> SeedSelectorOutput:
        """
        Parse the response from the model.
        :param response: the response from the model
        :param input: the input of the tool
        :return: the output of the tool
        """
        if "Answer" not in response:
            return None
        
        index_answer = response.index("Answer")
        final_answer = response[index_answer + len("Answer"):]
        if "No" in final_answer.lower():
            output = SeedSelectorOutput([])
        else:
            numbers = re.findall(r'\d+', final_answer)
            seed_list = []
            for number in numbers:
                line_number = int(number)
                for value in input.seed_list:
                    if value.line_number == line_number + input.seed_function.start_line_number - 1:
                        seed_list.append(value)
            output = SeedSelectorOutput(seed_list)
        print("Output of seed_selector:\n", str(output))
        return output
