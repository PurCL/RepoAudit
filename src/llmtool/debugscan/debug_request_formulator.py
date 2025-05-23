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


class DebugRequestFormulatorInput(LLMToolInput):
    def __init__(
        self,
        error_message: str,
        lined_function_code: str,
        error_file_path: str,
        request: str,
    ) -> None:
        """
        :param error_message: the error message
        :param request: the request
        """
        self.error_message = error_message
        self.lined_function_code = lined_function_code
        self.error_file_path = error_file_path
        self.request = request
        return

    def __hash__(self) -> int:
        return hash((self.error_message, self.request))


class DebugRequestFormulatorOutput(LLMToolOutput):
    def __init__(self, debug_seed: Value, request: str) -> None:
        self.debug_seed = debug_seed
        self.request = request
        return

    def __str__(self):
        return f"Debug Request Formulator Output: {self.debug_seed}, {self.request}"


class DebugRequestFormulator(LLMTool):
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
            f"{BASE_PATH}/prompt/{language}/debugscan/debug_request_formulator.json"
        )
        return

    def _get_prompt(self, debug_request_formulator_input: LLMToolInput) -> str:
        if not isinstance(debug_request_formulator_input, DebugRequestFormulatorInput):
            raise TypeError(
                f"Input type {type(debug_request_formulator_input)} is not supported for {type(self).__name__}."
            )

        with open(self.prompt_file, "r") as f:
            prompt_template_dict = json.load(f)

        prompt = prompt_template_dict["task"]
        prompt += "\n" + "".join(prompt_template_dict["meta_prompts"])
        prompt = prompt.replace(
            "<ANSWER>", "\n".join(prompt_template_dict["answer_format"])
        )
        prompt = prompt.replace(
            "<ERRMSG>", debug_request_formulator_input.error_message
        )
        prompt = prompt.replace(
            "<LINED_FUNCTION_CODE>", debug_request_formulator_input.lined_function_code
        )
        return prompt

    def _parse_response(
        self,
        response: str,
        debug_request_formulator_input: Optional[LLMToolInput] = None,
    ) -> Optional[LLMToolOutput]:
        """
        Parse the response from the model.
        :param response: the string response from the model
        :param debug_request_formulator_input: the input of the model
        :return: the output of the tool
        """
        if not isinstance(debug_request_formulator_input, DebugRequestFormulatorInput):
            raise TypeError(
                f"Input type {type(debug_request_formulator_input)} is not supported for {type(self).__name__}."
            )

        print("Response:", response)
        pattern = r"- Expression Name:\s*(\w+)[,;]?\s*\n- Line Number:\s*(\d+)[,;]?\s*\n- File Name:\s*([\w.]+)"
        match = re.search(pattern, response, re.MULTILINE)
        if match:
            expr = match.group(1)
            line_number = match.group(2)
            file_name = match.group(3)

            if not line_number.isdigit():
                print("Invalid line number format")
                return None

            debug_seed = Value(
                expr,
                int(line_number),
                ValueLabel.SINK,
                debug_request_formulator_input.error_file_path,
            )
            output = DebugRequestFormulatorOutput(
                debug_seed, debug_request_formulator_input.request
            )
            return output
        else:
            print("No match found")
            return None
