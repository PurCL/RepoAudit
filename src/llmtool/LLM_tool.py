from .LLM_utils import *
from abc import ABC, abstractmethod
from typing import Dict


class LLMToolInput(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def __hash__(self):
        pass


class LLMToolOutput(ABC):
    def __init__(self):
        pass


class LLMTool(ABC):
    def __init__(self,
                 model_name: str, 
                 temperature: float,
                 language: str,
                 max_query_num: int
                 ) -> None:
        self.language = language
        self.model_name = model_name
        self.temperature = temperature
        self.language = language
        self.max_query_num = max_query_num

        self.model = LLM(model_name, temperature)
        self.cache : Dict[LLMToolInput, LLMToolOutput] = {}

        self.input_token_cost = 0
        self.output_token_cost = 0
        self.total_query_num = 0

    def invoke(self, input: LLMToolInput) -> LLMToolOutput:
        print("LLM tool is invoked.")
        if input in self.cache:
            print("Cache hit.")
            return self.cache[input]
        
        prompt = self._get_prompt(input)
        single_query_num = 0
        output = None
        while True:
            if single_query_num > self.max_query_num:
                break
            single_query_num += 1
            response, input_token_cost, output_token_cost = self.model.infer(prompt, True)
            self.input_token_cost += input_token_cost
            self.output_token_cost += output_token_cost
            output = self._parse_response(response, input)
            if output is not None:
                break
        
        print(response)
        self.total_query_num += single_query_num
        if output is not None:
            self.cache[input] = output
        return output
    
    @abstractmethod
    def _get_prompt(self, input: LLMToolInput) -> str:
        pass

    @abstractmethod
    def _parse_response(self, response: str, input: LLMToolInput = None) -> LLMToolOutput:
        pass
