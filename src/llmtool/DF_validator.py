from pathlib import Path
import json
import time
from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from .LLM_utils import *
from memory.semantic.dfa_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *
from llmtool.LLM_tool import *
BASE_PATH = Path(__file__).resolve().parents[1]

class DataFlowValidator(LLMTool):
    """
    Forward slicer class
    """
    def __init__(
            self, 
            model_name, 
            temperature, 
            language,
            bug_type
            ) -> None:
        self.bug_type = bug_type
        self.prompt_file = f"{BASE_PATH}/prompt/{language}/{bug_type}/validation_prompt.json"
        super().__init__(model_name, temperature, language)
        self.bug_type_prompt = {
            "NPD": "Null Pointer Dereference",
            "UAF": "Use After Free",
            "MLK": "Memory Leak",
        }

    def validate(self, path: str, explanation: str, function: str) -> Tuple[bool, dict]:
        """
        Determine the reachability of the path using LLM, return True if the path is reachable
        :param path: the path to be validated
        :param explanation: the explanation of the path
        :param function: the function where the path is located
        :return: a boolean value indicating the reachability of the path and the query information
        """
        prompt = self.get_prompt(path, explanation, function)
        return self.query_LLM(prompt, "validation")


    def get_prompt(self, path: str, explanation: str, function: str,) -> str:
        """
        Generate prompt for the given path
        """
        bug_type_prompt = self.bug_type_prompt[self.bug_type]
        with open(self.prompt_file, "r") as read_file:
            dump_config_dict = json.load(read_file)
        question_template = dump_config_dict["question_template"]

        question_template = "\n".join(question_template)
    
        question = (
            question_template.replace("<BUG_TYPE>", bug_type_prompt)
            .replace("<PATH>", path)
            .replace("<EXPLANATION>", explanation)
        )

        answer_format = "\n".join(dump_config_dict["answer_format"])

        prompt = dump_config_dict["task"]
        prompt += "\n" + "\n".join(dump_config_dict["analysis_rules"])
        prompt += "\n" + "\n".join(dump_config_dict["analysis_examples"])
        prompt += "\n" + "".join(dump_config_dict["meta_prompts"])
        prompt = (
            prompt.replace("<PROGRAM>", function)
            .replace("<QUESTION>", question)
            .replace("<ANSWER>", answer_format)
        )
        return prompt

    def query_LLM(self, message: str, key:str) -> Tuple[bool, dict]:
        """
        Query the LLM model with the given message
        """
        current_query_num = 0
        while current_query_num < self.MAX_QUERY_NUM:
            start_time = time.time()

            response, input_token_cost, output_token_cost = self.model.infer(message)
            
            query_info = {}
            query_info["message"] = message
            query_info["answer"] = response
            query_info["query_time"] = time.time() - start_time
            query_info["input_token_cost"] = input_token_cost
            query_info["output_token_cost"] = output_token_cost

            self.query_num += 1
            print(response)
            answer_match = re.search(r'Answer:\s*(\w+)', response)
            if answer_match:
                answer = answer_match.group(1).strip()
                break
            else:
                print(f"Answer not found in validation output")
        flag = "yes" in answer.lower()
        return flag, query_info

    def fetch_system_role(self):
        with open(self.prompt_file, "r") as read_file:
            dump_config_dict = json.load(read_file)
        role = dump_config_dict["system_role"].replace("<LANGUAGE>", self.language)
        return role
