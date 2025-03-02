from os import path
import json
import time
from parser.base_parser import *
from parser.C_parser import *
from .utils import *
from utility.state import State
from utility.function import *
from utility.localvalue import *
from LMAgent.LM_agent import *
BASE_PATH = Path(__file__).resolve().parents[1]

class Top2BotAnalyzer(LLMAgent):
    """
    Neumeric analyzer
    """
    def __init__(
            self, 
            model_name, 
            temp, 
            language, 
            ts_analyzer, 
            is_fscot, 
            boundary,
            ) -> None:
        self.prompt_file = f"{BASE_PATH}/prompt/slicing/top2bot_prompt.json"
        super().__init__(model_name, language, is_fscot)
        system_role = self.fetch_system_role()
        self.model = LLM(model_name, temp, system_role)
        self.ts_analyzer = ts_analyzer
        self.boundary = boundary

        self.src_type_prompt = {
            ValueType.BUF: "buffer size and index of",
            ValueType.RET: "return value",
            ValueType.ARG: "argument",
        }
        self.slice_pattern = r'Slicing:\s*(.*?)\s*External variables:'
        self.exeternal_pattern = r'External variables:\s*((?:-.*(?:\n|$))+)' 
        self.var_pattern = (
            r'^\s*(?:-\s*)?Source:\s*(?P<source>[^.]+)\.' 
            r'(?:\s*Function Name:\s*(?P<function>[^\n.]+))?'  # optional function name
            r'(?:\s*Index:\s*(?P<index>\d+))?'                # optional index
            r'(?:\s*Variable Name:\s*(?P<variable>[^\n.]+))?'   # optional variable name
        )


    def analyze(self, state: State, depth: int) -> bool:
        """
        Analyze the state
        """
        if depth > self.boundary:
            return False
        
        key = str(state.var) + state.function.function_name
        if key in self.cache:
            print(f"Cache hit: {key}")
        else:
            message = self.get_prompt(state)
            if (not self.query_LLM(message, key)):
                return False

        state.slice = self.cache[key].slice
        for external_variable in self.cache[key].external_variables:
            source = external_variable["source"]
            value = external_variable["value"]
            if source == "Return Value":
                callee_name = value
                callee_functions = self.ts_analyzer.get_callee_functions(state.function, callee_name)
                for callee_function in callee_functions:
                    src = LocalValue("", 0, ValueType.RET, callee_function.file_name)
                    callee_state = State(src, callee_function)
                    if (self.analyze(callee_state, depth+1)):
                        state.callees.append(callee_state)
                        callee_state.callers.append(state)
            # for callee functions, we don't need to retrieve their callers.
            if source == "Parameter" and state.var.v_type != ValueType.RET:
                index = value
                caller_functions = self.ts_analyzer.get_caller_functions(state.function)
                for caller_function in caller_functions:
                    callee_name = state.function.function_name
                    argments = self.ts_analyzer.get_argument_by_index(caller_function, callee_name, int(value)-1)
                    for arg in argments:
                        caller_state = State(arg, caller_function)
                        if (self.analyze(caller_state, depth+1)):
                            state.callers.append(caller_state)
                            caller_state.callees.append(state)
            if source == "Global Variable":
                global_variable_name = value
                if global_variable_name in self.ts_analyzer.glb_var_map:
                    macro = f"{global_variable_name} = {self.ts_analyzer.glb_var_map[global_variable_name]}"
                    state.slice += "\n" + macro
        return True


    def get_prompt(self, state: State) -> str:
        """
        Generate the prompt
        """
        src_name = state.var.name
        src_type = self.src_type_prompt[state.var.v_type] if state.var.v_type in self.src_type_prompt else ""
        src_line_number = state.get_src_line()
        if state.function.lined_code == "":
            self.function_processor.transform(state.function.function_code)
            state.function.lined_code = self.function_processor.lined_code

        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)

        message = dump_config_dict["task"]
        message += "\n" + "\n".join(dump_config_dict["analysis_rules"])

        if self.is_fscot:
            message += "\n" + "\n".join(dump_config_dict["analysis_examples"])
            answer = self.fetch_answer_format_fscot()
        else:
            answer = self.fetch_answer_format_no_fscot()

        message += "\n" + "".join(dump_config_dict["meta_prompts"])
        message = message.replace("<FUNCTION>", state.function.lined_code)
        question = (
            dump_config_dict["question_template"].replace("<SRC_NAME>", src_name)
            .replace("<SRC_LINE>", f"at line {src_line_number}" if state.var.v_type != ValueType.RET else "")
            .replace("<SRC_TYPE>", src_type)
        )
        message = message.replace("<QUESTION>", question)
        message = message.replace("<ANSWER>", answer)

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

            self.result_list.append(query_result)
            self.query_num += 1

            # parse the output
            lines =  output.split("\n")
            idx = 0
            for line in lines:
                if line.startswith("Answer:"):
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

            var_match = re.search(self.exeternal_pattern, answer, re.DOTALL)
            if var_match:
                var_lines = var_match.group(1).splitlines()
                for line in var_lines:
                    m = re.match(self.var_pattern, line)
                    if not m:
                        continue
                    source = m.group("source")
                    if source == "Parameter":
                        index = m.group("index")
                        self.cache[key].add_external_variable("Parameter", index)
                    if source == "Global Variable":
                        global_variable_name = m.group("variable")
                        self.cache[key].add_external_variable("Global Variable", global_variable_name)
                    if source == "Return Value":
                        callee_name = m.group("function")
                        self.cache[key].add_external_variable("Return Value", callee_name)
    
        if format_error != "":
            print(f"Format error in {self.MAX_QUERY_NUM} queries")
            return False   
        return True


    def fetch_system_role(self):
        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        role = dump_config_dict["system_role"].replace("<LANGUAGE>", self.language)
        return role


    def fetch_answer_format_fscot(self) -> str:
        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        answer_format = dump_config_dict["answer_format_cot"]
        return "\n".join(answer_format)


    def fetch_answer_format_no_fscot(self) -> str:
        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        answer_format = dump_config_dict["answer_format_no_cot"]
        return "\n".join(answer_format)