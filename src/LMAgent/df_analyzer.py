from os import path
import json
import time
import time
from parser.response_parser import *
from parser.program_parser import *
from parser.ts_transform import *
from utility.llm import *
from utility.df_state import *
from utility.function import *
from utility.localvalue import *
from LMAgent.LM_agent import LMAgent

class DataflowAnalyzer(LMAgent):
    """
    Dataflow analyzer
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
            bug_type,
            sink_functions
            ) -> None:
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
        self.sink_functions = sink_functions
        self.cache = {}
        self.input_token_cost = 0
        self.output_token_cost = 0
        self.query_num = 0
        self.result_list = []
        self.src_type_prompt = {
            ValueType.SRC: "",
            ValueType.RET: "return value of",
            ValueType.PARA: "parameter of",
            ValueType.ARG: "argument of",
        }


    def search(self, src:LocalValue, function: Function, depth: int) -> State:
        """
        Search the path from source to sink
        """
        if depth > self.boundary:
            return None
        
        key = str(src.line_number) + function.function_name
        if key in self.cache:
            print(f"Cache hit: {key}")
            return self.cache[key]


        # query the model
        print(str(src))
        state = State(src, function)

        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)

        if self.is_fscot:
            message = self.prompt_fscot
            answer = self.fetch_answer_format_fscot()
        else: 
            message = self.prompt_no_fscot
            answer = self.fetch_answer_format_no_fscot()
        
        message += "\n" + "".join(dump_config_dict["meta_prompts"])

        self.function_processor.transform(state.function.function_code)
        state.function.code_without_comments = self.function_processor.code_without_comments
        state.function.lined_code_without_comments = self.function_processor.lined_code_without_comments

        message = message.replace(
            "<FUNCTION>", state.function.lined_code_without_comments
        )

        src_type = self.src_type_prompt[state.source.v_type] if state.source.v_type in self.src_type_prompt else ""
        src_line_number = state.get_src_line()
        question = (
            dump_config_dict["question_template"].replace("<SRC_NAME>", state.source.name)
            .replace("<SRC_LINE>", str(src_line_number))
            .replace("<SRC_TYPE>", src_type)
        )
        message = message.replace("<QUESTION>", question)
        message = message.replace("<ANSWER>", answer)
        message = message.replace("<SRC_NAME>", state.source.name).replace("<SRC_LINE>", str(src_line_number))

        key_points = self.construct_key_points_prompt(state.function)
        message = message.replace("<KEY_POINTS>", key_points)
        message = message.replace("<SINK>", self.conduct_sink_function_prompt())

        format_error = " "
        while format_error != "":
            start_time = time.time()

            format_error = ""
            output, input_token_cost, output_token_cost = self.model.infer(
                message, True
                )
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
            lines = lines[idx+1:]
            
            path_pattern = r"(Lines|Line) (?P<lines>.+?)\. Status: (?P<status>\w+)"
            callee_pattern = r"- Callee: (?P<callee>.+?)\. Argument: (?P<argument>\d+)\. Propagation Line: (?P<line_number>\d+)\. Dependency: (?P<dependency>.+)"
            caller_pattern = r"- Caller. Type: (?P<type>.+?)\. Index: (?P<index>.+?)\. Propagation Line: (?P<line_number>\d+)\. Dependency: (?P<dependency>.+)"
            safe_pattern = r"- Dependency: (?P<dependency>.+)"

            current_path = None
            for line in lines:
                if line.startswith("Path"):
                    match = re.search(path_pattern, line)
                    if not match:
                        format_error = f"Path format error: {line}"
                        break
                    lines = match.group("lines")
                    status = match.group("status")
                    current_path = Path(lines, state, status)
                    state.subpath.append(current_path)
                
                if line.startswith("-"):
                    if not current_path:
                        format_error = "Path not found"
                        break
                    status = current_path.get_status()

                    if status == "Safe":
                        match = re.search(safe_pattern, line)
                        if not match:
                            format_error = f"Safe format error {line}"
                            break
                        dependency = match.group("dependency")
                        current_path.dependency = dependency
                    
                    if status == "Bug":
                        if self.bug_type == "ML":
                            bug_pattern = r"- Dependency: (?P<dependency>.+)"
                            match = re.search(bug_pattern, line)
                            if not match:
                                format_error = f"Bug format error {line}"
                                break
                            dependency = match.group("dependency")
                            current_path.dependency = dependency
                        
                        if self.bug_type == "NPD" or self.bug_type == "UAF":
                            if self.bug_type == "NPD":
                                bug_pattern = r"- (Lines|Line) (?P<line>\d+)\. Deference Operation: `(?P<deference_operation>[^`]+)`\. Dependency: (?P<dependency>.+)"
                            else:
                                bug_pattern = r"- (Lines|Line) (?P<line>\d+)\. (Usage Operation|Deference Operation|Free Operation): `(?P<deference_operation>[^`]+)`\. Dependency: (?P<dependency>.+)"
                            match = re.search(bug_pattern, line)
                            if not match:
                                format_error = f"Bug format error {line}"
                                break
                            deference_line = match.group('line')
                            deference_operation = match.group('deference_operation')
                            dependency = match.group('dependency')
                            sink_line = int(deference_line) + state.function.start_line_number - 1
                            sink_point = LocalValue(deference_operation, sink_line, ValueType.SINK, state.function.file_name)
                            current_path.sink = sink_point
                            current_path.dependency = dependency


                    if status == "Unknown":
                        if line.startswith("- Callee"):
                            match = re.search(callee_pattern, line)
                            if not match:
                                format_error = f"Callee format error {line}"
                                break
                                # print(f"Callee format error {line}")
                                # continue
                            callee_name = match.group('callee')
                            argument = match.group('argument')
                            dependency = match.group('dependency')
                            sink_line = int(match.group('line_number')) + state.function.start_line_number - 1
                            if "->" in dependency:
                                continue
                            argument_num = int(argument)

                            callee_functions = self.ts_analyzer.get_callee_functions_by_name(state.function, callee_name)
                            for callee_function in callee_functions:
                                src = self.ts_analyzer.get_parameter_by_index(callee_function, argument_num)
                                if not src:
                                    continue
                                callee_state = self.search(src, callee_function, depth+1)
                                if not callee_state:
                                    continue
                                current_path.add_child(callee_state, dependency, "callee", sink_line)

                        if line.startswith("- Caller"):
                            match = re.search(caller_pattern, line)
                            if not match:
                                format_error = f"Caller format error {line}"
                                break
                                # print(f"Caller format error {line}")
                                # continue
                            type = match.group('type')
                            index = match.group('index')
                            dependency = match.group('dependency')
                            sink_line = int(match.group('line_number')) + state.function.start_line_number - 1
                            if "->" in dependency:
                                continue
                            if type == "Return":
                                caller_functions = self.ts_analyzer.get_caller_functions(state.function)
                                for caller_function in caller_functions:
                                    callee_name = state.function.function_name
                                    call_sites = self.ts_analyzer.get_call_site_by_callee_name(caller_function, callee_name)

                                    for src in call_sites:
                                        caller_state = self.search(src, caller_function, depth+1)
                                        if not caller_state:
                                            continue
                                        current_path.add_child(caller_state, dependency, "return", sink_line)
                            if type == "Pointer Parameters":
                                try:
                                    index = int(index)
                                except:
                                    print(f"Index error: {line}")
                                    continue
                                caller_functions = self.ts_analyzer.get_caller_functions(state.function)
                                for caller_function in caller_functions:
                                    callee_name = state.function.function_name
                                    pointer_arg = self.ts_analyzer.get_argument_by_index(caller_function, callee_name, index)
                                    for src in pointer_arg:
                                        caller_state = self.search(src, caller_function, depth+1)
                                        if not caller_state:
                                            continue
                                        current_path.add_child(caller_state, dependency, "pointer parameter", sink_line)
                    
            if format_error != "":
                print(format_error)
                continue
        self.cache[key] = state
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
            "But these key points may contain some operations not related to the source. "
            "You still need to analyze the alias of source pointer and extract the ones that are related to the source pointer and its alias. "
            "These key points include: \n"
        )

        key_points = self.ts_analyzer.extract_key_points(function, self.bug_type)
        if not key_points:
            return ""
        for key_point in key_points:
            key_point_info_template += f"- Line {key_point.line_number}: {key_point.name}\n"
        return key_point_info_template
    
    def conduct_sink_function_prompt(self) -> str:
        """
        Conduct the sink function prompt
        """
        if not self.sink_functions:
            return ""
        if self.bug_type == "NPD":
            sink_function_prompt = "You can also see the following functions as deference operations:\n"
        if self.bug_type == "UAF":
            sink_function_prompt = "You can also see the following functions as usage operations:\n"
        if self.bug_type == "ML":
            sink_function_prompt = "You can also see the following functions as free operations:\n"

        for sink_function in self.sink_functions:
            sink_function_prompt += f"- {sink_function}\n"
        return sink_function_prompt
