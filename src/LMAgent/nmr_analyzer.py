from os import path
import json
import time
import time
from parser.response_parser import *
from parser.program_parser import *
from parser.ts_transform import *
from utility.llm import *
from utility.nmr_state import State
from utility.function import *
from utility.localvalue import *
from LMAgent.LM_agent import LMAgent


class NeumericAnalyzer(LMAgent):
    """
    Neumeric analyzer
    """
    def __init__(
            self, 
            prompt_file, 
            online_model_name, 
            temp, 
            language, 
            ts_analyzer, 
            function_processor, 
            is_fscot, 
            boundary, 
            bug_type
            ) -> None:
        super().__init__()
        self.prompt_file = prompt_file
        self.language = language
        system_role = self.fetch_system_role()
        self.model = LLM(online_model_name, temp, system_role)
        self.ts_analyzer = ts_analyzer
        self.function_processor = function_processor
        self.is_fscot = is_fscot
        self.boundary = boundary
        self.bug_type = bug_type
        self.cache = {}
        self.input_token_cost = 0
        self.output_token_cost = 0
        self.query_num = 0
        self.result_list = []
        self.MAX_QUERY_NUM = 10
        self.src_type_prompt = {
            ValueType.VAR: "integer variable",
            ValueType.BUF: "buffer",
            ValueType.RET: "return value",
            ValueType.ARG: "argument",
        }

    def analyze(self, state: State, depth: int) -> bool:
        """
        Analyze the state
        """
        if depth > self.boundary:
            return False
        
        key = str(state.var) + state.function.function_name
        if key in self.cache:
            print(f"Cache hit: {key}")
            state.expressions.extend(self.cache[key].expressions)
            state.children.extend(self.cache[key].children)
            return True
        self.cache[key] = state

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

        print(f"\n Function: \n{state.function.lined_code}")

        format_error = " "
        current_query_num = 0
        while format_error != "" and current_query_num < self.MAX_QUERY_NUM:
            current_query_num += 1
            start_time = time.time()

            format_error = ""
            output, input_token_cost, output_token_cost = self.model.infer(
                message, True
                )
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

            expr_pattern = r'Expressions:\s*(.*?)\s*External variables:'
            expr_match = re.search(expr_pattern, answer, re.DOTALL)
            expressons = []
            if expr_match:
                expressons.extend(expr_match.group(1).strip().splitlines())
            else:
                format_error = "Expressions not found"
                print(f"Format error: {format_error}")
                continue
            
            if state.abs != "":
                for expression in expressons:
                    left_value = expression.split("=")[0].strip()
                    expression = expression.replace(left_value, state.abs)
                    state.expressions.append(expression)
            else:
                state.expressions.extend(expressons)

            var_pattern = r'External variables:\s*((?:-.*(?:\n|$))+)' 
            var_match = re.search(var_pattern, answer, re.DOTALL)
            if var_match:
                var_lines = var_match.group(1).splitlines()
                for line in var_lines:
                    var_pattern = (
                        r'-\s*Name:\s*(?P<name>[^.]+)\.\s*'
                        r'Source:\s*(?P<source>[^.]+)\.'  
                        r'(?:\s*Function Name:\s*(?P<function>[^\n.]+))?'  # optional function name
                        r'(?:\s*Index:\s*(?P<index>\d+))?'                # optional index
                        r'(?:\s*Variable Name:\s*(?P<variable>[^\n.]+))?'   # optional variable name
                    )
                    m = re.match(var_pattern, line)
                    if not m:
                        continue
                    name = m.group("name")
                    source = m.group("source")
                    if source == "Parameter":
                        index = m.group("index")
                        caller_functions = self.ts_analyzer.get_caller_functions(state.function)
                        for caller_function in caller_functions:
                            callee_name = state.function.function_name
                            argments = self.ts_analyzer.get_argument_by_index(caller_function, callee_name, int(index)-1)
                            for arg in argments:
                                child_state = State(arg, caller_function, name)
                                self.analyze(child_state, depth+1)
                                state.children.append(child_state)
                    if source == "Global Variable":
                        global_variable_name = m.group("variable")
                        if global_variable_name in self.ts_analyzer.macro_map:
                            expresson = f"{global_variable_name} = {self.ts_analyzer.macro_map[global_variable_name]}"
                            child_state = State(LocalValue(global_variable_name, 0, ValueType.VAR, ""), state.function, name)
                            child_state.expressions.append(expresson)
                            state.children.append(child_state)
                    if source == "Return Value":
                        callee_name = m.group("function")
                        callee_functions = self.ts_analyzer.get_callee_functions_by_name(state.function, callee_name)
                        for callee_function in callee_functions:
                            src = LocalValue("", 0, ValueType.RET, callee_function.file_name)
                            child_state = State(src, callee_function, name)
                            self.analyze(child_state, depth+1)
                            state.children.append(child_state)
    
        if format_error != "":
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