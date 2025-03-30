from os import path
import json
import time
from typing import List, Set, Optional, Dict
from .LLM_utils import *
from .LLM_tool import *
from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.syntactic.api import *
BASE_PATH = Path(__file__).resolve().parents[1]

class IntraDataFlowAnalyzerInput(LLMToolInput):
    def __init__(
        self, 
        function: Function, 
        summary_start: Value, 
        sink_values: List[Tuple[str, int]], 
        call_statements: List[Tuple[str, int]], 
        ret_values: List[Tuple[str, int]]
    ) -> None:
        self.function = function
        self.summary_start = summary_start
        self.sink_values = sink_values
        self.call_statements = call_statements
        self.ret_values = ret_values
        return

    def __hash__(self) -> int:
        return hash((self.function.function_id, str(self.summary_start)))
        

class IntraDataFlowAnalyzerOutput(LLMToolOutput):
    def __init__(self, reachable_values: List[Set[Value]]) -> None:
        self.reachable_values = reachable_values
        return


class IntraDataFlowAnalyzer(LLMTool):
    def __init__(self, model_name: str, temperature: float, language: str, max_query_num: int) -> None:
        """
        :param model_name: the model name
        :param temperature: the temperature
        :param language: the programming language
        :param max_query_num: the maximum number of queries if the model fails
        """
        super().__init__(model_name, temperature, language, max_query_num)
        self.dfa_prompt_file = f"{BASE_PATH}/prompt/{language}/{language}_intra_dfa_prompt.json"
        return

    def _get_prompt(self, input: IntraDataFlowAnalyzerInput) -> str:
        with open(self.dfa_prompt_file, "r") as f:
            prompt_template_dict = json.load(f)
        prompt = prompt_template_dict["task"]
        prompt += "\n" + "\n".join(prompt_template_dict["analysis_rules"])
        prompt += "\n" + "".join(prompt_template_dict["meta_prompts"])
        prompt = prompt.replace("<ANSWER>", "\n".join(prompt_template_dict["answer_format_cot"]))
        prompt = prompt.replace("<QUESTION>", prompt_template_dict["question_template"])

        prompt = (
            prompt.replace("<FUNCTION>", input.function.lined_code)
                .replace("<SRC_NAME>", input.summary_start.name)
                .replace("<SRC_LINE>", str(input.summary_start.line_number - input.function.start_line_number + 1))
        )
        
        sinks_str = "Sink values in this function:\n"
        for sink_value in input.sink_values:
            sinks_str += f"- {sink_value[0]} at line {sink_value[1]}\n"
        prompt = prompt.replace("<SINK_VALUES>", sinks_str)

        calls_str = "Call statements in this function:\n"
        for call_statement in input.call_statements:
            calls_str += f"- {call_statement[0]} at line {call_statement[1]}\n"
        prompt = prompt.replace("<CALL_STATEMENTS>", calls_str)

        rets_str = "Return values in this function:\n"
        for ret_val in input.ret_values:
            rets_str += f"- {ret_val[0]} at line {ret_val[1]}\n"
        prompt = prompt.replace("<RETURN_VALUES>", rets_str)
        return prompt
    
    def _parse_response(self, response: str, input: IntraDataFlowAnalyzerInput) -> IntraDataFlowAnalyzerOutput:
        """
        Parse the LLM response to extract all execution paths and their propagation details.
        
        Expected response format for each path:
        
        - Path <Path Number>: <Execution Path>.
            - Type: <type>; Name: <name>; Function: <function>; Index: <index>; Line: <line>; Dependency: <dependency>
            - (optionally, multiple propagation details per path)
        
        Returns:
            The output of the intra-procedural data-flow analyzer that contains a list of reachable values
        """
        paths = []
        
        # Regex to match a path header line, e.g.,
        # "- Path 0: Single execution path through lines 1 → 2 → 3."
        path_header_re = re.compile(r"^- Path\s+(\d+):\s*(.+?)[\.;]$")
        
        # Regex to match a propagation detail line, e.g.,
        # "    - Type: Return; Name: null; Function: None; Index: 0; Line: 3; Dependency: SRC (null) is directly returned ... "
        detail_re = re.compile(
            r"^\s*-\s*Type:\s*([^;]+);\s*Name:\s*([^;]+);\s*Function:\s*([^;]+);\s*Index:\s*([^;]+);\s*Line:\s*([^;]+);\s*Dependency:\s*(.+)$"
        )
        
        current_path = None
        for line in response.splitlines():
            line = line.strip("\n")
            if not line.strip():
                continue
                
            # Check for path header
            header_match = path_header_re.match(line)
            if header_match:
                if current_path:
                    paths.append(current_path)
                current_path = {
                    "path_number": header_match.group(1).strip(),
                    "execution_path": header_match.group(2).strip(),
                    "propagation_details": []
                }
            else:
                # Check for propagation detail line (should be indented)
                detail_match = detail_re.match(line)
                if detail_match and current_path is not None:
                    detail = {
                        "type": detail_match.group(1).strip(),
                        "name": detail_match.group(2).strip(),
                        "function": detail_match.group(3).strip(),
                        "index": detail_match.group(4).strip(),
                        "line": detail_match.group(5).strip(),
                        "dependency": detail_match.group(6).strip()
                    }
                    current_path["propagation_details"].append(detail)
        
        # Append last path if not yet added
        if current_path:
            paths.append(current_path)

        reachable_values = []
        file_path = input.function.file_path
        start_line_number = input.function.start_line_number

        for single_path in paths:
            reachable_values_per_path = set([])
            for detail in single_path["propagation_details"]:
                
                if detail["type"] == "Argument":
                    reachable_values_per_path.add(Value(detail["name"], int(detail["line"]) + start_line_number - 1, ValueLabel.ARG, file_path, int(detail["index"])))
                if detail["type"] == "Parameter":
                    reachable_values_per_path.add(Value(detail["name"], int(detail["line"]) + start_line_number - 1, ValueLabel.PARA, file_path, int(detail["index"])))
                if detail["type"] == "Return":
                    reachable_values_per_path.add(Value(detail["name"], int(detail["line"]) + start_line_number - 1, ValueLabel.RET, file_path, int(detail["index"])))
                if detail["type"] == "Sink":
                    reachable_values_per_path.add(Value(detail["name"], int(detail["line"]) + start_line_number - 1, ValueLabel.SINK, file_path))
            reachable_values.append(reachable_values_per_path)

        output = IntraDataFlowAnalyzerOutput(reachable_values)
        print(output.reachable_values)
        return output
