import json
from pathlib import Path
from typing import List, Tuple
from utility.localvalue import *
from utility.function import *


class LMAgent:
    """
    LMAgent class for neuro-based analysis
    """

    def __init__(self) -> None:
        self.total_input_token_cost = 0
        self.total_output_token_cost = 0
        self.time_cost = 0
        self.prompt_config_file_base = (
            Path(__file__).resolve().parent.parent.absolute() / "prompt"
        )

    def construct_general_prompt(
        self, config_file_path: str, is_propagation: bool
    ) -> Tuple[str, str]:
        """
        Construct the prompt according to prompt config file
        """
        with open(self.prompt_config_file_base / config_file_path, "r") as read_file:
            dump_config_dict = json.load(read_file)
        system_role = dump_config_dict["system_role"]
        prompt = dump_config_dict["task"]
        prompt += "\n" + "\n".join(dump_config_dict["analysis_rules"])
        prompt += "\n" + "\n".join(dump_config_dict["analysis_examples"])
        prompt += "\n" + "".join(dump_config_dict["meta_prompts"])
        prompt += "\n" + "".join(dump_config_dict["output_constraints"])
        prompt += "\n" + "\n".join(dump_config_dict["output_examples"])
        prompt += "\n" + "Here is the program:"
        return system_role, prompt

    @staticmethod
    def process_response_item_lines(
        response: str, v_type: ValueType
    ) -> List[LocalValue]:
        """
        Process the response of the model.
        """
        response_lines = response.split("\n")
        items = []
        for line in response_lines:
            comma_index = line.find(",")
            name_seg = line[:comma_index]
            line_seg = line[comma_index + 1 :]
            ind = name_seg.find(":")
            val_name = name_seg[ind + 1 :].strip()
            val_line = line_seg.split(" ")[-1]
            if val_line.isdigit():
                items.append(LocalValue(val_name, int(val_line), v_type))
        return items

    @staticmethod
    def process_yes_no_list_in_response(response: str) -> List[str]:
        tmp = (
            response.replace(",", " ")
            .replace(".", "")
            .replace("\n", " ")
            .replace("-", "")
            .replace("System:", "")
            .replace('"', "")
        )
        ans = []
        for s in tmp.split(" "):
            if s not in {"Yes", "No"}:
                continue
            ans.append(s)
        return ans
