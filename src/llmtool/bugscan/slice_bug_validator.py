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


class SliceBugValidatorInput(LLMToolInput):
    def __init__(
        self,
        buggy_construct_str: str,
        functions_str: str,
        call_tree: str,
        explanation_str: str,
    ) -> None:
        """
        :param buggy_construct_str: the string indicating the buggy construct
        :param functions_str: the string indicating the original functions
        :param call_tree: the string indicating the call tree
        :param explanation_str: the explanation of the bug
        """
        self.buggy_construct_str = buggy_construct_str
        self.functions_str = functions_str
        self.call_tree = call_tree
        self.explanation_str = explanation_str
        return

    def __hash__(self) -> int:
        return hash(
            (
                str(self.buggy_construct_str),
                self.functions_str,
                self.call_tree,
                self.explanation_str,
            )
        )


class SliceBugValidatorOutput(LLMToolOutput):
    def __init__(
        self,
        is_buggy: bool,
        targeted_construct_str: str,
        detection_explanation_str: str,
        validation_explanation_str: str,
    ) -> None:
        """
        :param is_buggy: whether the construct is buggy.
        :param targeted_construct_str: the string indicating the targeted construct
        :param detection_explanation_str: the explanation in the detection of the bug
        :param validation_explanation_str: the explanation in the validation of the bug
        """
        self.is_buggy = is_buggy
        self.targeted_construct_str = targeted_construct_str
        self.detection_explanation_str = detection_explanation_str
        self.validation_explanation_str = validation_explanation_str
        return

    def __str__(self):
        return f"Is buggy: {self.is_buggy} \nDetection explanation: {self.detection_explanation_str} \nValidation explanation: {self.validation_explanation_str}"


class SliceBugValidator(LLMTool):
    def __init__(
        self,
        bug_type: str,
        model_name: str,
        temperature: float,
        language: str,
        max_query_num: int,
        logger: Logger,
    ) -> None:
        """
        :param bug_type: the type of bug to detect
        :param model_name: the model name
        :param temperature: the temperature
        :param language: the programming language
        :param max_query_num: the maximum number of queries if the model fails
        :param logger: the logger
        """
        super().__init__(model_name, temperature, language, max_query_num, logger)
        self.bug_type = bug_type
        self.prompt_file = (
            f"{BASE_PATH}/prompt/{language}/bugscan/{bug_type}_slice_bug_validator.json"
        )
        return

    def _get_prompt(self, input: LLMToolInput) -> str:
        """
        :param input: the input of intra-procedural detector
        :return: the prompt string
        """
        if not isinstance(input, SliceBugValidatorInput):
            raise TypeError(
                f"Input type {type(input)} is not supported for {type(self).__name__}."
            )

        with open(self.prompt_file, "r") as f:
            prompt_template_dict = json.load(f)
        prompt = prompt_template_dict["task"]
        prompt += "\n" + "\n".join(prompt_template_dict["validation_rules"])
        prompt += "\n" + "\n".join(prompt_template_dict["validation_examples"])
        prompt += "\n" + "\n".join(prompt_template_dict["meta_prompts"])

        prompt = prompt.replace(
            "<ANSWER>", "\n".join(prompt_template_dict["answer_format"])
        )
        prompt = prompt.replace("<QUESTION>", prompt_template_dict["question_template"])
        prompt = prompt.replace("<CODE_SNIPPET>", input.functions_str)
        prompt = prompt.replace("<SEED_DESCRIPTION>", str(input.buggy_construct_str))
        prompt = prompt.replace("<FUNCTION_CALL_TREE>", input.call_tree)
        prompt = prompt.replace("<LLM_BUG_REPORT>", input.explanation_str)
        return prompt

    def _parse_response(
        self, response: str, input: Optional[LLMToolInput] = None
    ) -> Optional[LLMToolOutput]:
        """
        :param response: the string response from the model
        :return: the output of intra-procedural detector
        """
        if not isinstance(input, SliceBugValidatorInput):
            raise TypeError(
                f"Input type {type(input)} is not supported for {type(self).__name__}."
            )

        answer_match = re.search(r"Answer:\s*(\w+)", response)
        explanation_match = re.search(r"Explanation:\s*(.*)", response, re.DOTALL)

        if answer_match and explanation_match:
            answer = answer_match.group(1).strip()
            explanation = explanation_match.group(1).strip()
            output = SliceBugValidatorOutput(
                answer == "Valid",
                input.buggy_construct_str,
                input.explanation_str,
                explanation,
            )
            self.logger.print_log("Output of slice bug validator:\n", str(output))
        else:
            self.logger.print_log("Answer or explanation not found in output")
            output = None
        return output
