from .LLM_utils import *
from abc import ABC, abstractmethod


class Cache:
    def __init__(self, slice: str, external_variables: list = []) -> None:
        self.slice = slice
        self.external_variables = external_variables

    def add_external_variable(self, source: str, value: str) -> None:
        self.external_variables.append({"source": source, "value": value})


class LLMTool(ABC):
    def __init__(self,
                 model_name: str, 
                 language: str
                 ) -> None:
        self.language = language
        self.model_name = model_name
        self.model = LLM(model_name)
        self.cache: dict[str, Cache] = {}
        self.input_token_cost = 0
        self.output_token_cost = 0
        self.query_num = 0
        self.result_list = []
        self.MAX_QUERY_NUM = 5


    @abstractmethod
    def analyze(self, state, depth: int) -> bool:
        """
        Analyze the code for a given state and return the analysis results.
        :param state: The current state object containing the function, variables, etc.
        :param depth: The depth of the analysis or the recursion level
        :return: A boolean value indicating whether the analysis was successful
        """
        pass

    @abstractmethod
    def get_prompt(self, state) -> str:
        """
        Generate a prompt for querying the LLM based on the current state.
        :param state: The current state object containing the relevant code and metadata
        :return: The prompt string for querying the LLM
        """
        pass

    @abstractmethod
    def query_LLM(self, message: str, key: str) -> bool:
        """
        Query the LLM with the given message and cache the results.
        :param message: The message or prompt to send to the LLM
        :param key: The key to use for caching the results
        :return: A boolean value indicating whether the query was successful
        """
        pass

