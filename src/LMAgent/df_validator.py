from os import path
import json

from parser.response_parser import *
from parser.program_parser import *
from parser.ts_transform import *
from utility.llm import *
from utility.df_state import *
from utility.function import *
from utility.localvalue import *
from LMAgent.LM_agent import LMAgent

class DataFlowValidator(LMAgent):
    """
    DataFlowValidator class for checking whether given inter-procedural paths are feasible or not
    """

    def __init__(self, prompt_file: str, model_name, temp, language, bug_type) -> None:
        super().__init__()
        self.validate_prompt_file = prompt_file
        self.language = language
        self.bug_type = bug_type
        system_role = self.fetch_system_role()
        self.response_path_check = ""
        self.model = LLM(model_name, temp, system_role)


    def validate_with_LLM(
        self,
        path: str,
        explanation: str,
        function: str,
    ) -> bool:
        """
        Determine the feasibility of the path using LLM
        """
        with open(self.validate_prompt_file, "r") as read_file:
            dump_config_dict = json.load(read_file)
        question_template = dump_config_dict["question_template"]

        question_template = "\n".join(question_template)
    
        question = (
            question_template.replace("<BUG_TYPE>", self.bug_type)
            .replace("<PATH>", path)
            .replace("<EXPLANATION>", explanation)
        )

        answer_format = self.fetch_path_check_answer_format()

        prompt = dump_config_dict["task"]
        prompt += "\n" + "\n".join(dump_config_dict["analysis_rules"])
        prompt += "\n" + "\n".join(dump_config_dict["analysis_examples"])
        prompt += "\n" + "".join(dump_config_dict["meta_prompts"])
        prompt = (
            prompt.replace("<PROGRAM>", function)
            .replace("<QUESTION>", question)
            .replace("<ANSWER>", answer_format)
        )
        # print("Prompt: ", prompt)
        
        while True:

            response, input_token_cost, output_token_cost = self.model.infer(prompt)
            print("====================================")
            print("Response: ", response)
            print("===============================================")
            self.total_input_token_cost += input_token_cost
            self.total_output_token_cost += output_token_cost
            self.response_path_check = response

            yes_no_vector = self.process_yes_no_list_in_response(
                self.response_path_check
            )
            if len(yes_no_vector) == 0:
                continue
            if "Yes" in yes_no_vector[0] or "yes" in yes_no_vector[0]:
                return True
            else:
                return False

    def fetch_system_role(self):
        with open(self.validate_prompt_file, "r") as read_file:
            dump_config_dict = json.load(read_file)
        role = dump_config_dict["system_role"].replace("<LANGUAGE>", self.language)
        return role

    def fetch_path_check_answer_format(self) -> str:
        with open(self.validate_prompt_file, "r") as read_file:
            dump_config_dict = json.load(read_file)
        answer_format = "\n".join(dump_config_dict["answer_format"])
        return answer_format