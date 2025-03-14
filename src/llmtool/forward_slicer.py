from os import path
import json
import time
from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from .LLM_utils import *
from memory.semantic.bugscan_state import BugScanState
from memory.syntactic.function import *
from memory.syntactic.value import *
from llmtool.LLM_tool import *
BASE_PATH = Path(__file__).resolve().parents[1]

class ForwardSlicer(LLMTool):
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
            ) -> None:
        self.prompt_file = f"{BASE_PATH}/prompt/llmtool/{language}/{language}_forward_prompt.json"
        super().__init__(model_name, temperature, language)
        self.cache = {str, Cache}
        self.ts_analyzer = ts_analyzer
        self.boundary = boundary

        self.seed_type_prompt = {
            ValueLabel.SRC: "variable",                 # start point
            ValueLabel.PARA: "parameters",              # goto callee
            ValueLabel.OUT: "return value of",          # goto caller
            ValueLabel.ARG: "arguments",                # goto caller
        }

        self.slice_pattern = r'Slicing:\s*(.*?)\s*External Propagation:'
        self.external_pattern = r'External Propagation:\s*((?:-.*(?:\n|$))+)' 
        self.var_pattern = (
            r'^\s*-\s*Type:\s*(?P<type>[^.]+)\.'
            r'(?:\s*Callee:\s*(?:(?:[^.]+\.)*(?P<callee_name>[^.]+))\.)?'  # optional callee name for arguments
            r'(?:\s*Index:\s*(?P<index>\d+))?'        # optional index for parameters/arguments
            r'(?:\s*Name:\s*(?P<variable_name>[^\n.]+))?'      # optional name for global variables
        )

    def analyze(self, state: BugScanState, depth: int) -> bool:
        """
        Analyze the state
        """
        if depth >= self.boundary:
            return False
        
        key = str(state.var) + state.function.function_name
        if key in self.cache:
            print(f"Cache hit: {key}")
        else:
            message = self.get_prompt(state)
            if (not self.query_LLM(message, key)):
                return False

        state.slice = self.cache[key].slice
        arg_set = set()           # store the index of parameters
        para_dict = {}            # store the callee name and indexes of arguments
        for external_variable in self.cache[key].external_variables:
            source_type = external_variable["type"]

            # For callee functions, the source variable is parameter, we don't need to retrieve their callers.
            if source_type == "Return Value" and state.var.label != ValueLabel.PARA:
                caller_functions = self.ts_analyzer.get_all_caller_functions(state.function)
                for caller_function in caller_functions:
                    call_site_nodes = self.ts_analyzer.get_callsite_by_callee_name(caller_function, state.function.function_name)
                    for call_site_node in call_site_nodes:
                        output_value = self.ts_analyzer.get_output_value_at_callsite(caller_function, call_site_node)
                        caller_state = BugScanState(output_value, caller_function)
                        if (self.analyze(caller_state, depth + 1)):
                            state.callers.append(caller_state)
                            caller_state.callees.append(state)
            if source_type == "Parameter":
                index = int(external_variable["index"])
                arg_set.add(index)
            if source_type == "Argument":
                callee_name = external_variable["callee_name"]
                index = int(external_variable["index"])
                if callee_name not in para_dict:
                    para_dict[callee_name] = set()
                para_dict[callee_name].add(index)
            if source_type == "Global Variable":
                # TODO: add global variable support
                pass

        # For callee functions, the source variable is parameter, we don't need to retrieve their callers.
        # When retrieving caller functions, we analyze all arguments in one query.
        if arg_set and state.var.label != ValueLabel.PARA:
            caller_functions = self.ts_analyzer.get_all_caller_functions(state.function)
            for caller_function in caller_functions:
                callee_name = state.function.function_name
                
                argments = set([])
                call_site_nodes = self.ts_analyzer.get_callsite_by_callee_name(caller_function, callee_name)
                for call_site in call_site_nodes:
                    argments.update(self.ts_analyzer.get_arguments_at_callsite(caller_function, call_site))
                argments = [arg for arg in argments if arg.index in arg_set]
                arg_names = ",".join([arg.name for arg in argments])
                max_line_number = max([arg.line_number for arg in argments])

                # TODO: TO BE Refactored. @Jinyao
                # ValueLabel.ARG refers to a single argument. The following construction of Value does not have a valid physical meaning.
                # Suggestion: Construct n arguments seperately and feed the list of values to the state. (State class might need to refactored too.)
                argment = Value(arg_names, max_line_number, ValueLabel.ARG, caller_function.file_name)
                caller_state = BugScanState(argment, caller_function)
                if (self.analyze(caller_state, depth+1)):
                    state.callers.append(caller_state)
                    caller_state.callees.append(state)

        # When retrieving callee functions, we analyze all parameters in one query.    
        for callee_name, index_set in para_dict.items():
            callee_functions = self.ts_analyzer.get_all_callee_functions(state.function, callee_name)
            for callee_function in callee_functions:
                parameter_list = []
                paras = self.ts_analyzer.get_parameters_in_single_function(callee_function)
                for index in index_set:
                    for para in paras:
                        if para.index == index:
                            parameter_list.append(para)
                parameter_names = ", ".join([parameter.name for parameter in parameter_list])
                parameter_line_number = min([parameter.line_number for parameter in parameter_list])

                # TODO: TO BE Refactored. @Jinyao
                # ValueLabel.PARA refers to a single parameter. The following construction of Value does not have a valid physical meaning.
                # Suggestion: Construct n parameters seperately and feed the list of values to the state. (State class might need to refactored too.)
                parameters = Value(parameter_names, parameter_line_number, ValueLabel.PARA, callee_function.file_name)
                callee_state = BugScanState(parameters, callee_function)
                if (self.analyze(callee_state, depth+1)):
                    state.callees.append(callee_state)
                    callee_state.callers.append(state)

        ## For DEBUG
        print(f"Finish analysis: {state.var.name} in {state.function.function_name}")
        return True


    def get_prompt(self, state: BugScanState) -> str:
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
            dump_config_dict["question_template"].replace("<SEED_NAME>", src_name)
            .replace("<SRC_LINE>", f"at line {src_line_number}")
            .replace("<SRC_TYPE>", src_type)
        )
        message = message.replace("<QUESTION>", question)
        message = message.replace("<ANSWER>", answer_format)

        ## For DEBUG
        print(f"\n Function: \n{state.function.lined_code}")

        return message


    def query_LLM(self, message: str, key:str) -> bool:
        """
        Query the LLM model
        :message: the prompt message
        :key: the key to cache the result
        """
        format_error = " "
        current_query_num = 0
        while format_error != "" and current_query_num < self.MAX_QUERY_NUM:
            current_query_num += 1
            start_time = time.time()

            format_error = ""
            output, input_token_cost, output_token_cost = self.model.infer(message, True)
            
            ## For DEBUG
            print(f"\nOutput: \n{output}")

            query_result = {}
            query_result["message"] = message
            query_result["answer"] = output
            query_result["query_time"] = time.time() - start_time
            query_result["input_token_cost"] = input_token_cost
            query_result["output_token_cost"] = output_token_cost
            print(f"Query time: {time.time() - start_time}")

            self.result_list.append(query_result)
            self.query_num += 1

            # parse the output
            lines =  output.split("\n")
            idx = 0
            for line in lines:
                if "Answer:" in line:
                    break
                idx += 1
            answer = "\n".join(lines[idx+1:])

            slice_match = re.search(self.slice_pattern, answer, re.DOTALL)
            if slice_match:
                self.cache[key] = Cache(slice_match.group(1).strip())
            else:
                format_error = "Slice not found"
                print(f"Format error: {format_error}")
                continue
            var_match = re.search(self.external_pattern, answer, re.DOTALL)
            if var_match:
                var_lines = var_match.group(1).splitlines()
                for line in var_lines:
                    match = re.match(self.var_pattern, line)
                    if not match:
                        continue
                    print(match.groupdict())
                    # Format Check
                    if match["type"] not in ["Return Value", "Parameter", "Argument", "Global Variable"]:
                        continue
                    if match["type"] == "Parameter" and match["index"] is None:
                        continue
                    if match["type"] == "Argument" and (match["callee_name"] is None or match["index"] is None):
                        continue
                    if match["type"] == "Global Variable" and match["variable_name"] is None:
                        continue
                    if match["index"] is not None:
                        if not match["index"].isdigit():
                            continue
                    self.cache[key].add_external_variable(match.groupdict())
    
        if format_error != "":
            print(f"Format error in {self.MAX_QUERY_NUM} queries")
            return False   
        return True


    def fetch_system_role(self):
        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        role = dump_config_dict["system_role"].replace("<LANGUAGE>", self.language)
        return role
