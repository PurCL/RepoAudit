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


class PathValidatorInput(LLMToolInput):
    def __init__(
        self,
        bug_type: str,
        values: List[Value],
        values_to_functions: Dict[Value, Function],
    ) -> None:
        self.bug_type = bug_type
        self.values = values
        self.values_to_functions = values_to_functions
        return

    def __hash__(self) -> int:
        return hash(str([str(value) for value in self.values]))


class PathValidatorOutput(LLMToolOutput):
    def __init__(self, is_reachable: bool, explanation_str: str) -> None:
        self.is_reachable = is_reachable
        self.explanation_str = explanation_str
        return

    def __str__(self):
        return (
            f"Is reachable: {self.is_reachable} \nExplanation: {self.explanation_str}"
        )


class PathValidator(LLMTool):
    def __init__(
        self,
        model_name: str,
        temperature: float,
        language: str,
        max_query_num: int,
        logger: Logger,
    ) -> None:
        """
        :param model_name: the model name
        :param temperature: the temperature
        :param language: the programming language
        :param max_query_num: the maximum number of queries if the model fails
        :param logger: the logger
        """
        super().__init__(model_name, temperature, language, max_query_num, logger)
        self.prompt_file = f"{BASE_PATH}/prompt/{language}/dfbscan/path_validator.json"
        return

    def _get_prompt(self, input: PathValidatorInput) -> str:
        with open(self.prompt_file, "r") as f:
            prompt_template_dict = json.load(f)
        prompt = prompt_template_dict["task"]
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_rules"])
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_examples"])
        prompt += "\n" + "".join(prompt_template_dict["meta_prompts"])
        prompt = prompt.replace(
            "<ANSWER>", "\n".join(prompt_template_dict["answer_format"])
        ).replace("<QUESTION>", "\n".join(prompt_template_dict["question_template"]))

        value_lines = []
        for value in input.values:
            value_line = " - " + str(value)
            function = input.values_to_functions.get(value)
            if function is None:
                continue
            value_line += (
                " in the function "
                + function.function_name
                + " at the line "
                + str(value.line_number - function.start_line_number + 1)
            )
            value_lines.append(value_line)
        prompt = prompt.replace("<PATH>", "\n".join(value_lines))
        prompt = prompt.replace("<BUG_TYPE>", input.bug_type)

        program = "\n".join(
            [
                "```\n" + func.lined_code + "\n```\n"
                for func in input.values_to_functions.values()
            ]
        )
        prompt = prompt.replace("<PROGRAM>", program)
        return prompt

    def _parse_response(
        self, response: str, input: PathValidatorInput
    ) -> PathValidatorOutput:
        answer_match = re.search(r"Answer:\s*(\w+)", response)
        if answer_match:
            answer = answer_match.group(1).strip()
            output = PathValidatorOutput(answer == "Yes", response)
            self.logger.print_log("Output of path_validator:\n", str(output))
        else:
            self.logger.print_log(f"Answer not found in output")
            output = None
        return output
