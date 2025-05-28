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


class CallerCalleeAnalyzerInput(LLMToolInput):
    def __init__(
        self,
        caller_function: Function,
        call_site_line_number_in_function: int,
        callee_candidates: List[Function],
    ) -> None:
        """
        :param caller_function: the caller function
        :param call_site_line_number_in_function: the line number of the call site in the caller function
        :param callee_candidates: the candidates of the callee
        """
        self.caller_function = caller_function
        self.call_site_line_number_in_function = call_site_line_number_in_function
        self.callee_candidates = callee_candidates
        return

    def __hash__(self) -> int:
        sorted_callee_ids = sorted(
            [callee.function_id for callee in self.callee_candidates]
        )
        return hash(
            (
                self.caller_function.function_id,
                self.call_site_line_number_in_function,
                str(sorted_callee_ids),
            )
        )


class CallerCalleeAnalyzerOutput(LLMToolOutput):
    def __init__(self, callee_ids: List[int]) -> None:
        """
        callee_ids: the ids of the callee functions
        """
        self.callee_ids = callee_ids
        return

    def __str__(self) -> str:
        return f"Callee IDs: {self.callee_ids}"


class CallerCalleeAnalyzer(LLMTool):
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
            f"{BASE_PATH}/prompt/{language}/cgscan/caller_callee_analyzer.json"
        )
        return

    def _get_prompt(self, caller_callee_analyzer: LLMToolInput) -> str:
        if not isinstance(caller_callee_analyzer, CallerCalleeAnalyzerInput):
            raise RAValueError(
                f"Input type {type(caller_callee_analyzer)} is not supported."
            )

        with open(self.prompt_file, "r") as f:
            prompt_template_dict = json.load(f)

        prompt = prompt_template_dict["task"]
        prompt += "\n" + "".join(prompt_template_dict["meta_prompts"])
        prompt = prompt.replace(
            "<CALLER_FUNCTION>", caller_callee_analyzer.caller_function.lined_code
        )
        prompt = prompt.replace(
            "<LINE_NUMBER>",
            str(caller_callee_analyzer.call_site_line_number_in_function),
        )

        callee_candidates_with_ids = ""
        for callee in caller_callee_analyzer.callee_candidates:
            callee_candidates_with_ids += "----------------------------------------\n"
            callee_candidates_with_ids += f"Function ID: {callee.function_id}\n"
            callee_candidates_with_ids += f"File Name: {callee.file_path}\n"
            callee_candidates_with_ids += (
                f"Function Code:\n\n```\n{callee.lined_code}\n```\n\n"
            )

        prompt = prompt.replace(
            "<CANDIDATE_CALLEE_FUNCTIONS_WITH_IDS>", callee_candidates_with_ids
        )

        prompt = prompt.replace(
            "<ANSWER>", "\n".join(prompt_template_dict["answer_format"])
        )
        return prompt

    def _parse_response(
        self,
        response: str,
        caller_callee_analyzer: Optional[LLMToolInput] = None,
    ) -> Optional[LLMToolOutput]:
        """
        Parse the response from the model.
        :param response: the response from the model
        :param caller_callee_analyzer: the caller_callee_analyzer of the tool
        :return: the output of the tool
        """
        if not isinstance(caller_callee_analyzer, CallerCalleeAnalyzerInput):
            raise RAValueError(
                f"Input type {type(caller_callee_analyzer)} is not supported."
            )

        callee_ids = []
        for line in response.split("\n"):
            if "Callee functions:" in line and "[" in line and "]" in line:
                index1 = line.index("[")
                index2 = line.index("]")
                callee_ids_str = line[index1 + 1 : index2]
                callee_ids = [
                    int(id_str.strip())
                    for id_str in callee_ids_str.split(",")
                    if id_str.strip()
                ]
                break

        call_edge_analyzer_output = CallerCalleeAnalyzerOutput(callee_ids)
        return call_edge_analyzer_output
