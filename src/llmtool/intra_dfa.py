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

class IntraDataFlowAnalyzerInput(LLMToolInput):
    def __init__(self, function: Function, summary_start: Value) -> None:
        self.function = function
        self.summary_start = summary_start
        return

    def __hash__(self) -> int:
        return hash((self.function.function_id, self.single_function_str))
        

class IntraDataFlowAnalyzerOutput(LLMToolOutput):
    def __init__(self, reachable_values: List[Set[Value]]) -> None:
        self.reachable_values = reachable_values
        return


class IntraDataFlowAnalyzer(LLMTool):
    def __init__(self, model_name: str, temperature: float, language: str, max_query_num: int) -> None:
        """
        :param model_name: the model name
        :param temperature: the temperature
        :param language: the programming language
        :param max_query_num: the maximum number of queries if the model fails
        """
        super().__init__(model_name, temperature, language, max_query_num)
        self.dfa_prompt_file = f"{BASE_PATH}/prompt/llmtool/{language}/{language}_intra_dataflow_prompt.json"
        return

    def _get_prompt(self, input: IntraDataFlowAnalyzerInput) -> str:
        with open(self.dfa_prompt_file, "r") as f:
            prompt_template_dict = json.load(f)
        prompt = prompt_template_dict["task"]
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_rules"])
        prompt += "\n" + "".join(prompt_template_dict["meta_prompts"])
        prompt = prompt.replace("<ANSWER>", "\n".join(prompt_template_dict["answer_format"]))
        prompt = prompt.replace("<QUESTION>", prompt_template_dict["question_template"])
        # TODO
        return prompt

    def _parse_response(self, response: str) -> IntraDataFlowAnalyzerOutput:
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
        output = IntraDataFlowAnalyzerOutput()
        return output
