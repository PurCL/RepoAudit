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


class CalleeCallerAnalyzerInput(LLMToolInput):
    def __init__(
        self,
        callee_function: Function,
        potential_caller_functions: List[Function],
        caller_ids_to_call_site_node_ids: Dict[int, List[int]],
    ) -> None:
        self.callee_function = callee_function
        self.potential_caller_functions = potential_caller_functions
        self.caller_ids_to_call_site_node_ids = caller_ids_to_call_site_node_ids
        return

    def __hash__(self) -> int:
        return hash(self.callee_function.function_id)


class CalleeCallerAnalyzerOutput(LLMToolOutput):
    def __init__(self, caller_ids_to_call_site_node_ids: Dict[int, List[int]]) -> None:
        """
        caller_ids_to_call_site_node_ids: the ids of the caller functions to the call site node ids
        """
        self.caller_ids_to_call_site_node_ids = caller_ids_to_call_site_node_ids
        return

    def __str__(self) -> str:
        return f"Caller IDs: {self.caller_ids_to_call_site_node_ids}"


class CalleeCallerAnalyzer(LLMTool):
    def __init__(
        self,
        model_name: str,
        temperature: float,
        language: str,
        max_query_num: int,
        logger: Logger,
    ) -> None:
        super().__init__(model_name, temperature, language, max_query_num, logger)
        self.prompt_file = (
            f"{BASE_PATH}/prompt/{language}/cgscan/callee_caller_analyzer.json"
        )
        return

    def _get_prompt(self, callee_caller_analyzer_input: LLMToolInput) -> str:
        if not isinstance(callee_caller_analyzer_input, CalleeCallerAnalyzerInput):
            raise RAValueError(
                f"Input type {type(callee_caller_analyzer_input)} is not supported."
            )

        # XXX (Chengpeng): We do not distinguish different call sites in the caller function
        # that have the same names of callee functions.
        # Maybe imprecise though the introduced imprecision should be acceptable in most cases.

        with open(self.prompt_file, "r") as f:
            prompt_template_dict = json.load(f)

        prompt = prompt_template_dict["task"]
        prompt += "\n" + "".join(prompt_template_dict["meta_prompts"])
        prompt = prompt.replace(
            "<CALLEE_FUNCTION>", callee_caller_analyzer_input.callee_function.lined_code
        )

        caller_candidates_with_ids = ""
        for caller in callee_caller_analyzer_input.potential_caller_functions:
            caller_candidates_with_ids += "----------------------------------------\n"
            caller_candidates_with_ids += f"Function ID: {caller.function_id}\n"
            caller_candidates_with_ids += f"File Name: {caller.file_path}\n"
            caller_candidates_with_ids += (
                f"Function Code:\n\n```\n{caller.lined_code}\n```\n\n"
            )

        prompt = prompt.replace(
            "<CANDIDATE_CALLER_FUNCTIONS_WITH_IDS>", caller_candidates_with_ids
        )

        prompt = prompt.replace(
            "<ANSWER>", "\n".join(prompt_template_dict["answer_format"])
        )
        return prompt

    def _parse_response(
        self,
        response: str,
        callee_caller_analyzer_input: Optional[LLMToolInput] = None,
    ) -> Optional[LLMToolOutput]:
        """
        Parse the response from the model.
        :param response: the response from the model
        :param callee_caller_analyzer_input: the callee_caller_analyzer_input of the tool
        :return: the output of the tool
        """
        if not isinstance(callee_caller_analyzer_input, CalleeCallerAnalyzerInput):
            raise RAValueError(
                f"Input type {type(callee_caller_analyzer_input)} is not supported."
            )

        caller_ids = []
        for line in response.split("\n"):
            if "Caller functions:" in line and "[" in line and "]" in line:
                index1 = line.index("[")
                index2 = line.index("]")
                caller_ids_str = line[index1 + 1 : index2]
                caller_ids = [int(id_str) for id_str in caller_ids_str.split(",")]
                break

        refined_caller_ids_to_call_site_node_ids = {}
        for caller_id in caller_ids:
            refined_caller_ids_to_call_site_node_ids[caller_id] = (
                callee_caller_analyzer_input.caller_ids_to_call_site_node_ids[caller_id]
            )

        callee_caller_analyzer_output = CalleeCallerAnalyzerOutput(
            refined_caller_ids_to_call_site_node_ids
        )
        return callee_caller_analyzer_output
