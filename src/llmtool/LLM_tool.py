from .LLM_utils import *
from abc import ABC, abstractmethod


class Cache:
    def __init__(self, slice: str, external_variables: list[dict] = None) -> None:
        self.slice = slice
        self.__variable_format = {
            "type": "",
            "callee_name": "",
            "index": "",
            "variable_name": "",
        }
        self.external_variables = (
            external_variables if external_variables is not None else []
        )

    def add_external_variable(self, value_dict: dict) -> None:
        if value_dict.keys() == self.__variable_format.keys():
            self.external_variables.append(value_dict)


class LLMTool(ABC):
    def __init__(self, model_name: str, temperature: float, language: str) -> None:
        self.language = language
        self.model_name = model_name
        self.model = LLM(model_name)
        system_role = self.fetch_system_role()
        self.model = LLM(model_name, temperature, system_role)
        self.input_token_cost = 0
        self.output_token_cost = 0
        self.query_num = 0
        self.result_list = []
        self.MAX_QUERY_NUM = 5

    def fetch_system_role(self) -> str:
        return "You are a experienced programmer and good at understanding programs written in mainstream programming languages."
