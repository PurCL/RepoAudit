from os import path
import json

from parser.response_parser import *
from parser.program_parser import *
from parser.ts_transform import *
from utility.llm import *
from utility.state import *
from utility.function import *
from utility.localvalue import *
from LMAgent.LM_agent import LMAgent
from typing import List
from itertools import product

class TraceAnalyzer(LMAgent):
    """
    State
    """

    def __init__(self, prompt_file, online_model_name, temp, language, ts_analyzer, function_processor, is_fscot, boundary, bug_type) -> None:
        super().__init__()
        self.prompt_file = prompt_file
        self.language = language
        system_role = self.fetch_system_role()
        self.model = LLM(online_model_name, temp, system_role)
        self.prompt_fscot = self.construct_prompt_skeleton_fscot()
        self.prompt_no_fscot = self.construct_prompt_skeleton_no_fscot()
        self.ts_analyzer = ts_analyzer
        self.function_processor = function_processor
        self.is_fscot = is_fscot
        self.boundary = boundary
        self.bug_type = bug_type
        self.state_cache = {}

    def analyze(self, src: LocalValue) -> List[List[Operation]]:
        """
        Analyze the operation trace of src
        """
        src_function = self.ts_analyzer.get_function_from_localvalue(src)
        if src_function is None:
            return None
        state = self.search(src, src_function)
        trace_list: List[List[Operation]] = []
        extend_trace_list: List[List[Operation]] = []

        for i in range(self.boundary):
            trace_list = state.get_subpath() if extend_trace_list == [] else extend_trace_list
            extend_trace_list = []
            for subpath in trace_list:
                extend_trace_list.extend(self.analyze_path(subpath))

        print(f"Analysis result for {src.name} in function {src_function.function_name}:")
        print("Trace Number: ", len(extend_trace_list))
        for trace in extend_trace_list:
            temp = []
            for operation in trace:
                temp.append(str(operation))
            print(temp)

        return extend_trace_list


    def analyze_path(self, path: List[Operation]) -> List[List[Operation]]:
        """
        Analyze the operation trace of a path
        """
        for i, operation in enumerate(path):
            if type(operation) is not Operation:
                print(path)
                for item in path:
                    print(item)
            if operation.status in ("Freed", "UnAllocated"):
                # for Memory Leak Bug
                break
            if operation.type == "Free":
                # for Memory Leak Bug
                break
            if operation.type == "Global Variables":
                break
            if operation.type == "Invocation":
                # callee function
                function = self.ts_analyzer.environment[operation.function_id]
                callee_function = self.ts_analyzer.get_callee_functions_by_name(function, operation.callee_name)
                if not callee_function:
                    continue
                src = self.ts_analyzer.get_parameter_by_index(callee_function, operation.index)
                if not src:
                    continue
                callee_state = self.search(src, callee_function)
                replace_list = callee_state.get_subpath()
                path[i] = replace_list

            if operation.type == "Return":
                # return value
                if operation.is_propagate == False:
                    continue
                function = self.ts_analyzer.environment[operation.function_id]
                replace_list = []
                caller_functions = self.ts_analyzer.get_caller_functions(function)
                for caller_function in caller_functions:
                    src_name = function.function_name
                    call_sites = self.ts_analyzer.get_call_site_by_callee_name(caller_function, src_name)
                    for src in call_sites:
                        caller_state = self.search(src, caller_function)
                        replace_list.extend(caller_state.get_subpath())
                path[i] = replace_list

            if operation.type == "Pointer Parameters":
                # pointer parameter
                function = self.ts_analyzer.environment[operation.function_id]
                replace_list = []
                caller_functions = self.ts_analyzer.get_caller_functions(function)
                for caller_function in caller_functions:
                    callee_name = function.function_name
                    pointer_arg = self.ts_analyzer.get_argument_by_index(caller_function, callee_name, operation.index)
                    for src in pointer_arg:
                        caller_state = self.search(src, caller_function)
                        replace_list.extend(caller_state.get_subpath())
                path[i] = replace_list

            if operation.type == "Free":
                # free
                pass
        elements = [item if isinstance(item, list) else [item] for item in path]
        combinations = list(product(*elements))
        substitute_path = [list(combination) for combination in combinations]
        result = []
        for path in substitute_path:
            flatten_path = [item for sublist in path for item in (sublist if isinstance(sublist, list) else [sublist])]
            result.append(flatten_path)
        return result


    def search(self, src:LocalValue, function: Function) -> Function_State:
        key = src.name + function.function_name
        if key in self.state_cache:
            return self.state_cache[key]
        state = Function_State(src, function)

        # query the model
        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)

        if self.is_fscot:
            message = self.prompt_fscot
            answer = self.fetch_answer_format_fscot()
        else: 
            message = self.prompt_no_fscot
            answer = self.fetch_answer_format_no_fscot()
        
        message += "\n" + "".join(dump_config_dict["meta_prompts"])

        self.function_processor.transform(function.function_code)
        function.code_without_comments = self.function_processor.code_without_comments
        function.lined_code_without_comments = self.function_processor.lined_code_without_comments

        message = message.replace(
            "<FUNCTION>", function.lined_code_without_comments
        )

        src_line_number = state.get_src_line()
        question = dump_config_dict["question_template"].replace("<SRC_NAME>", src.name).replace("<SRC_LINE>", str(src_line_number))

        message = message.replace("<QUESTION>", question)
        message = message.replace("<ANSWER>", answer)
        message = message.replace("<SRC_NAME>", src.name).replace("<SRC_LINE>", str(src_line_number))

        key_points = self.construct_key_points_prompt(state.function)
        message = message.replace("<KEY_POINTS>", key_points)

        format_error = " "
        while format_error != "":
            format_error = ""
            output, input_token_cost, output_token_cost = self.model.infer(
                message, False
                ) 

            print(f"Current function: {state.function.function_name}")
            print(state.function.lined_code_without_comments)
            # print(f"Key points: {key_points}")
            print(f"Question: {question}")
            print("=======================================")
            print(output)
            print("=================================================================================")

            # parse the output
            lines =  output.split("\n")
            idx = 0
            for line in lines:
                if line.startswith("Answer:"):
                    break
                idx += 1
            lines = lines[idx+1:]

            path_pattern = r"(Lines|Line) (?P<lines>.+)\. Operation Trace: (?P<trace>.+)"
            operation_pattern = r'(<<.*?>>)'
            for line in lines:
                if line.startswith("Path"):
                    match = re.search(path_pattern, line)
                    if not match:
                        format_error = f"Path format error: {line}"
                        break
                    lines = match.group("lines")
                    trace = match.group("trace")
                    operation_list = re.findall(operation_pattern, trace)
                    op_trace = []
                    for operation in operation_list:
                        op_obj = Operation(operation, state.function.function_name, state.function.function_id, state.function.file_name)
                        if op_obj.error_message == "":
                            op_trace.append(op_obj)
                    if op_trace != [] and op_trace[0].type == "Source Point":
                        state.subpath.append(op_trace)
            if format_error != "":
                print(format_error)
                continue
        
        self.state_cache[key] = state
        return state


    def construct_prompt_skeleton_fscot(self) -> str:
        """
        Construct the prompt according to prompt config file
        :return: The prompt
        """
        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        prompt = dump_config_dict["task"]
        prompt += "\n" + "\n".join(dump_config_dict["analysis_rules"])
        prompt += "\n" + "\n".join(dump_config_dict["Detection_rules"])
        prompt += "\n" + "\n".join(dump_config_dict["analysis_examples"])
        return prompt

    
    def construct_prompt_skeleton_no_fscot(self) -> str:
        """
        Construct the prompt according to prompt config file
        :return: The prompt
        """
        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        prompt = dump_config_dict["task"]
        prompt += "\n" + "\n".join(dump_config_dict["analysis_rules"])
        prompt += "\n" + "\n".join(dump_config_dict["Detection_rules"])
        return prompt


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
    

    def construct_key_points_prompt(self, function:Function) -> str:
        """
        Construct the key points of the function
        """
        key_point_info_template = (
            "For your convinence in Step 1, here we provide some potential key points of the function. "
            "But these key points may contain some operations not related to src. "
            "You still need to analyze the alias of src and extract the ones that are related to src and its alias. "
            "These key points include: \n"
        )

        key_points = self.ts_analyzer.extract_key_points(function, self.bug_type)
        if not key_points:
            return ""
        for key_point in key_points:
            key_point_info_template += f"- Line {key_point.line_number}: {key_point.name}\n"
        return key_point_info_template
