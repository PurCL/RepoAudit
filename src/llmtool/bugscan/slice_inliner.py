from os import path
import json
import traceback
import time
from typing import List, Set, Optional, Dict
from llmtool.LLM_utils import *
from llmtool.LLM_tool import *
from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.syntactic.api import *

BASE_PATH = Path(__file__).resolve().parent.parent.parent


class SliceInlinerInput(LLMToolInput):
    def __init__(
        self,
        root_function_id: int,
        relevant_functions: Dict[int, Function],
        slice_items: List[Tuple[int, List[Value], str]],
        function_caller_to_callee_map: Dict[int, Set[int]],
    ) -> None:
        """
        :param root_function_id: the root function id
        :param relevant_functions: the relevant functions appearing in the slices
        :param slice_items: the slice cases containing (1) function id, (2) seed values, and (3) slice
        :param function_caller_to_callee_map: the mapping from caller functions to callee functions
        """
        self.root_function_id = root_function_id
        self.relevant_functions = relevant_functions
        self.slice_items = slice_items
        self.function_caller_to_callee_map = function_caller_to_callee_map
        self.tree_str = self.build_tree_str()
        return

    def build_tree_str(self) -> str:
        """
        :return: the string representation of the caller-callee tree that will be used in the prompt for slicing
        """
        lines = []
        visited = set()  # Track visited functions to detect cycles

        def traverse(func_id: int, prefix: str, is_last: bool, path: List[int]) -> None:
            # Check for cycles
            if func_id in path:
                # We found a cycle, mark it in the visualization
                cycle_start = path.index(func_id)
                cycle_path = path[cycle_start:] + [func_id]
                cycle_str = " -> ".join(
                    str(self.relevant_functions[id].function_name) for id in cycle_path
                )
                lines.append(f"{prefix}└── [CYCLE] {cycle_str}")
                return

            # Print the function name
            branch = "└── " if is_last else "├── "
            line = (
                prefix + branch + self.relevant_functions[func_id].function_name
                if prefix
                else self.relevant_functions[func_id].function_name
            )
            lines.append(line)

            # Only process children if we haven't visited this function before
            if func_id not in visited:
                visited.add(func_id)
                children: Set[int] = self.function_caller_to_callee_map.get(
                    func_id, set()
                )
                for i, child_id in enumerate(children):
                    child_is_last = i == len(children) - 1
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    traverse(child_id, new_prefix, child_is_last, path + [func_id])

        traverse(self.root_function_id, "", True, [])
        return "\n".join(lines)

    def __hash__(self) -> int:
        relevant_function_ids = sorted(self.relevant_functions.keys())
        slices_strs = []
        for function_id, seed_values, slice in self.slice_items:
            seed_values_strs = sorted([str(value) for value in seed_values])
            slices_strs.append(f"{function_id}, {str(seed_values_strs)}, {slice}")
        slices_str = str(slices_strs)
        function_caller_to_callee_map_strs = []
        for caller_id, callee_ids in self.function_caller_to_callee_map.items():
            function_caller_to_callee_map_strs.append(
                f"{caller_id}, {sorted(list(callee_ids))}"
            )
        function_caller_to_callee_map_str = str(
            sorted(function_caller_to_callee_map_strs)
        )
        return hash(
            (str(relevant_function_ids), slices_str, function_caller_to_callee_map_str)
        )


class SliceInlinerOutput(LLMToolOutput):
    def __init__(self, inlined_snippet: str) -> None:
        """
        :param inlined_snippet: the inlined snippet as the output of slicing
        """
        self.inlined_snippet = inlined_snippet
        return

    def __str__(self):
        return f"Inlined snippet: {self.inlined_snippet}"


class SliceInliner(LLMTool):
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
        self.prompt_file = f"{BASE_PATH}/prompt/{language}/bugscan/slice_inliner.json"
        return

    def _get_prompt(self, input: LLMToolInput) -> str:
        """
        :param input: the input of slice inliner
        :return: the prompt string
        """
        if not isinstance(input, SliceInlinerInput):
            raise TypeError(
                f"Input type {type(input)} is not supported for {type(self).__name__}."
            )

        with open(self.prompt_file, "r") as f:
            prompt_template_dict = json.load(f)

        role = prompt_template_dict["system_role"].replace("<LANGUAGE>", self.language)
        prompt = prompt_template_dict["task"]
        prompt += "\n" + "".join(prompt_template_dict["meta_prompts"])
        prompt = prompt.replace(
            "<ANSWER>", "\n".join(prompt_template_dict["answer_format"])
        )

        # append all the slices
        slices = []
        for function_id, seed_values, slice in input.slice_items:
            if function_id not in input.relevant_functions:
                continue
            slices.append(slice)
        prompt = prompt.replace("<FUNCTION>", "\n".join(slices))

        # append call tree
        call_tree_prompt = prompt_template_dict["call_tree"]
        call_tree_prompt = call_tree_prompt.replace(
            "<FUNCTION_NAME>",
            input.relevant_functions[input.root_function_id].function_name,
        )
        call_tree_prompt = call_tree_prompt.replace(
            "<FUNCTION_CALL_TREE>", input.tree_str
        )
        prompt += "\n" + call_tree_prompt
        return prompt

    def _parse_response(
        self, response: str, input: Optional[LLMToolInput] = None
    ) -> Optional[LLMToolOutput]:
        """
        :param response: the string response from the model
        :return: the output of slice inliner
        """
        if not isinstance(input, SliceInlinerInput):
            raise TypeError(
                f"Input type {type(input)} is not supported for {type(self).__name__}."
            )

        pattern = re.compile(r"```(?:\w+)?\s*([\s\S]*?)\s*```")
        match = pattern.search(response)
        if match:
            output = SliceInlinerOutput(match.group(1))
            self.logger.print_log(f"Inlined result: {output.inlined_snippet}")
        else:
            self.logger.print_log(f"Inline function not found in output")
            output = None
        return output
