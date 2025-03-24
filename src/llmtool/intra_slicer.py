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

class IntraSlicerInput(LLMToolInput):
    def __init__(self, function: Function, seed_list: List[Value], is_backward: bool = True) -> None:
        """
        :param function: the function to be sliced
        :param seed_set: the set of seed values
        :param is_backward: whether the slicing is backward
        """
        # Typically, there is only one seed. 
        # Here, we consider a set of seed values in the following two cases for efficiency improvement
        # (1) Return values of a given function
        # (2) The same program location with the same label
        # Otherwise, the seed list should have one slicing seed only.

        assert IntraSlicerInput.check_validity_of_seed_list(seed_list), "Invalid seed list"

        # Initialization
        self.function = function
        self.is_backward = is_backward
        self.seed_list = sorted(set(seed_list), key=lambda seed: (seed.index, seed.name))

        if len(self.seed_list) > 1:
            if self.seed_list[0].label != ValueLabel.RET:
                self.seed_type = self.seed_list[0].label
                self.seed_line_number = self.seed_list[0].line_number
                self.seed_name = ""
                for seed in self.seed_list:
                    self.seed_name += seed.name + ", "
            else:
                self.seed_name = "return values"
                self.seed_type = ""
                self.seed_line_number = -1
        else:
            self.seed_name = self.seed_list[0].name
            self.seed_type = self.seed_list[0].label
            self.seed_line_number = self.seed_list[0].line_number
        return
    
    @staticmethod
    def check_validity_of_seed_list(seed_list: List[Value]) -> bool:
        # Seed List Format Check
        ## Case 1: Return values of a given function
        labels = [seed.label for seed in seed_list]
        is_return = False
        if len(set(labels)) == 1 and ValueLabel.RET in labels:
            is_return = True
        
        ## Case 2: The same program location with the same label
        is_same_loc_label = len(set(seed_list)) > 1
        for seed_value1 in seed_list:
            for seed_value2 in seed_list:
                if seed_value1.file != seed_value2.file \
                or seed_value1.line_number != seed_value2.line_number \
                or seed_value1.label != seed_value2.label:
                    is_same_loc_label = False

        ## Case 3: The seed list should have one slicing seed only
        is_length_one = len(set(seed_list)) == 1
        return is_return or is_same_loc_label or is_length_one


    def __hash__(self) -> int:
        return hash((str(self.seed_list), self.function.function_id, self.is_backward))


class IntraSlicerOutput(LLMToolOutput):
    def __init__(self, slice: str, ext_values: List[Dict]) -> None:
        self.slice = slice
        """
        An external value is in the following form:
        {
            "type": str, 
            "callee_name": Optional[str], 
            "index": Optional[int], 
            "variable_name": Optional[str]
        }
        Here are several examples:
        {'type': 'Argument', 'callee_name': 'log_message', 'index': 0, 'variable_name': None}
        {'type': 'Return Value', 'callee_name': None, 'index': None, 'variable_name': None}
        {'type': 'Parameter', 'callee_name': None, 'index': 0, 'variable_name': None}
        {'type': 'Parameter', 'callee_name': None, 'index': 1, 'variable_name': None}
        {'type': 'Output Value', 'callee_name': 'goo', 'index': None, 'variable_name': None}
        """
        self.ext_values = ext_values


class IntraSlicer(LLMTool):
    def __init__(self, model_name: str, temperature: float, language: str, max_query_num: int) -> None:
        super().__init__(model_name, temperature, language, max_query_num)
        self.backward_prompt_file = f"{BASE_PATH}/prompt/{language}/{language}_backward_prompt.json"
        self.forward_prompt_file = f"{BASE_PATH}/prompt/{language}/{language}_forward_prompt.json"
        return

    def _get_prompt(self, input: IntraSlicerInput) -> str:
        prompt_file = self.forward_prompt_file if not input.is_backward else self.backward_prompt_file
        with open(prompt_file, "r") as f:
            prompt_template_dict = json.load(f)

        prompt = prompt_template_dict["task"]
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_rules"])
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_examples"])
        prompt += "\n" + "\n".join(prompt_template_dict["meta_prompts"])


        question = (
            prompt_template_dict["question_template"].replace("<SEED_NAME>", input.seed_name)
            .replace("<SEED_LINE>", "" if input.seed_line_number == -1 else f"line {input.seed_line_number}")
            .replace("<SEED_TYPE>", str(input.seed_type))
        )
        answer_format = "\n".join(prompt_template_dict["answer_format_cot"])

        prompt = prompt.replace("<FUNCTION>", input.function.lined_code)
        prompt = prompt.replace("<QUESTION>", question)
        prompt = prompt.replace("<ANSWER>", answer_format)
        return prompt


    def _parse_response(self, response: str, input: IntraSlicerInput) -> IntraSlicerOutput:
        slice_pattern = r'Slicing:\s*(.*?)\s*External Variables:'
        ext_values_pattern = r'External Variables:\s*((?:-.*(?:\n|$))+)' 
        var_pattern = (
            r'^\s*-\s*Type:\s*(?P<type>[^.]+)\.'
            r'(?:\s*Callee:\s*(?P<callee_name>[^.]+)\.)?'      # optional callee name for arguments
            r'(?:\s*Index:\s*(?P<index>\d+))?'                 # optional index for parameters/arguments
            r'(?:\s*Name:\s*(?P<variable_name>[^\n.]+))?'      # optional name for global variables
        )
    
        slice_match = re.search(slice_pattern, response, re.DOTALL)
        if slice_match:
            output_slice = slice_match.group(1).strip()
        else:
            format_error = "Slice not found"
            print(f"Format error: {format_error}")
            return None

        output_ext_values = []
        var_match = re.search(ext_values_pattern, response, re.DOTALL)
        if var_match:

            var_lines = var_match.group(1).splitlines()
            for line in var_lines:
                match = re.match(var_pattern, line)
                if not match:
                    continue
                if match["type"] not in ["Return Value", "Parameter", "Argument", "Global Variable", "Output Value"]:
                    continue
                if match["type"] == "Parameter" and match["index"] is None:
                    continue
                if match["type"] == "Argument" and (match["callee_name"] is None or match["index"] is None):
                    continue
                if match["type"] == "Global Variable" and match["variable_name"] is None:
                    continue
                if match["index"] == "Output Value" and match["callee_name"] is None:
                    continue
                ext_value = match.groupdict()
                if ext_value.get("index") is not None:
                    try:
                        ext_value["index"] = int(ext_value["index"])
                    except ValueError:
                        ext_value["index"] = None
                output_ext_values.append(ext_value)
        output = IntraSlicerOutput(output_slice, output_ext_values)
        return output
