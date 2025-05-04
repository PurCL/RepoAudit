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


class DataflowAnalyzer(LLMTool):
    """
    Forward slicer class
    """
    def __init__(
            self, 
            model_name, 
            temperature, 
            language, 
            ts_analyzer,
            boundary,
            bug_type
            ) -> None:
        self.bug_type = bug_type
        self.prompt_file = f"{BASE_PATH}/prompt/{language}/analysis_prompt.json"
        super().__init__(model_name, temperature, language)
        self.cache: Dict[str, DFAState] = {}
        self.ts_analyzer = ts_analyzer
        self.boundary = boundary
        self.total_input_token_cost = 0
        self.total_output_token_cost = 0

        self.seed_type_prompt = {
            ValueLabel.SRC: "",                         # start point
            ValueLabel.PARA: "parameter of",            # goto callee
            ValueLabel.OUT: "return value of",          # goto caller
            ValueLabel.ARG: "argument of",              # goto caller
        }

        self.path_pattern = r"(Lines|Line) (?P<lines>.+?)\."
        self.propagation_pattern = r"- Type: (?P<type>.+?)\. Function Name: (?P<function>.+?)\. Index: (?P<index>.+?)\. Line: (?P<line>.+?)\. Dependency: (?P<dependency>.+)"


    def get_prompt(self, state: DFAState) -> str:
        """
        Generate the prompt
        """
        src_name = state.var.name
        src_type = self.seed_type_prompt[state.var.label] if state.var.label in self.seed_type_prompt else ""
        src_line_number = state.get_src_line()

        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)

        message = dump_config_dict["task"]
        message += "\n" + "\n".join(dump_config_dict["analysis_rules"])
        message += "\n" + "\n".join(dump_config_dict["analysis_examples"])
        
        answer_format = "\n".join(dump_config_dict["answer_format_cot"])

        message += "\n" + "".join(dump_config_dict["meta_prompts"])
        message = message.replace("<FUNCTION>", state.function.lined_code)
        question = (
            dump_config_dict["question_template"].replace("<SRC_NAME>", src_name)
            .replace("<SRC_LINE>", str(src_line_number))
            .replace("<SRC_TYPE>", src_type)
        )
        message = message.replace("<QUESTION>", question)
        message = message.replace("<ANSWER>", answer_format)
        message = message.replace("<SRC_NAME>", src_name).replace("<SRC_LINE>", str(src_line_number))

        # TODO: Replace <SINK>, <CALL_STATEMENTS> and <RETURN_STATEMENTS>        

        return message

    def query_LLM(self, message: str) -> Tuple[list[dict], dict]:
        """
        Query the LLM, return the parsed result
        :param message: The message to be sent to the LLM
        :return: A tuple containing the parsed result and the query info
        Parsed result format:
        {   
            "path_lines": lines,
            "propagation_info": [{
                "type": "Argument",
                "function_name": callee_name,
                "index": index,
                "dependency": dependency,
                "line": callsite_line
                }]
        }
        """
        format_error = " "
        current_query_num = 0
        result: list[dict] = []
        while format_error != "" and current_query_num < self.MAX_QUERY_NUM:
            current_query_num += 1
            start_time = time.time()

            format_error = ""
            output, input_token_cost, output_token_cost = self.model.infer(
                message, True
                )
            query_info = {}
            query_info["message"] = message
            query_info["answer"] = output
            query_info["query_time"] = time.time() - start_time
            query_info["input_token_cost"] = input_token_cost
            query_info["output_token_cost"] = output_token_cost

            self.query_num += 1
            self.total_input_token_cost += input_token_cost
            self.total_output_token_cost += output_token_cost

            # parse the output
            lines =  output.split("\n")
            idx = 0
            for line in lines:
                if "Answer:" in line:
                    break
                idx += 1
            lines = lines[idx+1:]

            current_path = None
            for line in lines:
                if line.startswith("Path"):
                    match = re.search(self.path_pattern, line)
                    if not match:
                        format_error = f"Path format error: {line}"
                        break
                    lines = match.group("lines")
                    current_path = {"path_lines": lines}
                    result.append(current_path)
                
                if line.startswith("-"):
                    if not current_path:
                        format_error = "Path not found"
                        break
                    if "propagation_info" not in current_path:
                        current_path["propagation_info"] = []
                    match = re.search(self.propagation_pattern, line)
                    if not match:
                        format_error = f"Propagation format error {line}"
                        break
                    type = match.group('type')
                    function_name = match.group('function')
                    index = match.group('index')
                    line_number = match.group('line')
                    dependency = match.group('dependency')
                    current_path["propagation_info"].append({"type": type, "function_name": function_name, "index": index, "dependency": dependency, "line": line_number})

            if format_error != "":
                print(format_error)
                continue
        return result, query_info

    def fetch_system_role(self):
        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        role = dump_config_dict["system_role"].replace("<LANGUAGE>", self.language)
        return role