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
        self.prompt_file = f"{BASE_PATH}/prompt/DFA/{language}/{bug_type}/analysis_prompt.json"
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

        self.path_pattern = r"(Lines|Line) (?P<lines>.+?)\. Status: (?P<status>\w+)"
        self.callee_pattern = r"- Callee: (?P<callee>.+?)\. Argument: (?P<argument>\d+)\. Propagation Line: (?P<line_number>\d+)\. Dependency: (?P<dependency>.+)"
        self.caller_pattern = r"- Caller. Type: (?P<type>.+?)\. Index: (?P<index>.+?)\. Propagation Line: (?P<line_number>\d+)\. Dependency: (?P<dependency>.+)"
        self.safe_pattern = r"- Dependency: (?P<dependency>.+)"


    def analyze(self, state: DFAState, depth: int) -> Tuple[bool, list[dict]]:
        """
        Analyze the code for a given state and return the analysis results.
        :param state: The current state object containing the function, variables, etc.
        :param depth: The depth of the analysis or the recursion level
        :return: A boolean value indicating whether the analysis was successful
        """
        info_list = []
        flag = self.__analyze(state, depth, info_list)
        return flag, info_list
        
    def __analyze(self, state: DFAState, depth: int, info_list) -> bool:
        """
        Analyze the state
        """
        if depth >= self.boundary:
            return False
        
        key = str(state.var) + state.function.function_name
        if key in self.cache:
            print(f"Cache hit: {key}")
            result_list = self.cache[key]
        else:
            message = self.get_prompt(state)
            result_list, query_info = self.query_LLM(message)
            if result_list == []:
                return False
            info_list.append(query_info)
            self.cache[key] = result_list

        for path_info in result_list:
            status = path_info["path_status"]
            current_path = ExecutionPath(path_info["path_lines"], state, status)
            state.subpath.append(current_path)
            
            if status == "Safe":
                current_path.dependency = path_info["safe_info"]["dependency"]
            
            if status == "Bug":
                if self.bug_type == "MLK":
                    current_path.dependency = path_info["bug_info"]["dependency"]
                if self.bug_type == "NPD" or self.bug_type == "UAF":
                    try:
                        bug_line = int(path_info["bug_info"]["line"]) + state.function.start_line_number - 1
                    except:
                        print(f"Bug line error: {path_info}")
                        continue
                    current_path.dependency = path_info["bug_info"]["dependency"]
                    current_path.sink = Value(path_info["bug_info"]["operation"], bug_line, ValueLabel.SINK, state.function.file_name)
                    
            if status == "Unknown":
                for propagation_info in path_info["propagation_info"]:
                    dependency = propagation_info["dependency"]
                    if "->" in dependency:
                        continue
                    try:
                        sink_line = int(propagation_info["line"]) + state.function.start_line_number - 1
                    except:
                        print(f"Sink line error: {path_info}")
                        continue
                    if propagation_info["type"] == "Argument":
                        try:
                            index = int(propagation_info["index"])
                        except:
                            print(f"Argument index error: {path_info}")
                            continue
                        callee_functions = [
                            function
                            for function in self.ts_analyzer.get_all_callee_functions(state.function)
                            if function.function_name == propagation_info["function_name"]
                        ]
                        for callee_function in callee_functions:
                            for parameter in self.ts_analyzer.get_parameters_in_single_function(callee_function):
                                if parameter.index == index:
                                    src = parameter
                                    callee_state = DFAState(src, callee_function)
                                    if (self.__analyze(callee_state, depth+1, info_list)):
                                        current_path.add_child(callee_state, dependency, "argument", sink_line)
                    
                    if propagation_info["type"] == "Return":
                        # For callee functions, the source variable is parameter, we don't need to retrieve their callers.
                        if state.var.label == ValueLabel.PARA:
                            continue 
                        caller_functions = self.ts_analyzer.get_all_caller_functions(state.function)
                        for caller_function in caller_functions:
                            for callsite in self.ts_analyzer.get_callsite_by_callee_name(caller_function, state.function.function_name):
                                output_value = self.ts_analyzer.get_output_value_at_callsite(caller_function, callsite)
                                caller_state = DFAState(output_value, caller_function)
                                if (self.__analyze(caller_state, depth+1, info_list)):
                                    current_path.add_child(caller_state, dependency, "return", sink_line)
                    
                    if propagation_info["type"] == "Parameter":
                        # For callee functions, the source variable is parameter, we don't need to retrieve their callers.
                        if state.var.label == ValueLabel.PARA:
                            continue 
                        try:
                            index = int(propagation_info["index"])
                        except:
                            print(f"Parameter index error: {path_info}")
                            continue
                        caller_functions = self.ts_analyzer.get_all_caller_functions(state.function)
                        for caller_function in caller_functions:
                            callee_name = state.function.function_name
                            for callsite in self.ts_analyzer.get_callsite_by_callee_name(caller_function, callee_name):
                                for arg in self.ts_analyzer.get_arguments_at_callsite(caller_function, callsite):
                                    if arg.index == index:
                                        caller_state = DFAState(arg, caller_function)
                                        if (self.__analyze(caller_state, depth+1, info_list)):
                                            current_path.add_child(caller_state, dependency, "parameter", sink_line)
        return True

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

        key_points = self.construct_key_points_prompt(state.function)
        message = message.replace("<KEY_POINTS>", key_points)

        return message

    def query_LLM(self, message: str) -> Tuple[list[dict], dict]:
        """
        Query the LLM, return the parsed result
        :param message: The message to be sent to the LLM
        :return: A tuple containing the parsed result and the query info
        Parsed result format:
        {   
            "path_lines": lines, 
            "path_status": status, 
            "propagation_info": [{
                "type": "Argument",
                "function_name": callee_name,
                "index": index,
                "dependency": dependency,
                "line": callsite_line
                }], 
            "bug_info": {
                "operation": operation,
                "dependency": dependency,
                "line": line
                },
            "safe_info": {
                "dependency": dependency
                } 
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
                    status = match.group("status")
                    current_path = {"path_lines": lines, "path_status": status}
                    result.append(current_path)
                
                if line.startswith("-"):
                    if not current_path:
                        format_error = "Path not found"
                        break
                    status = current_path["path_status"]

                    if status == "Safe":
                        match = re.search(self.safe_pattern, line)
                        if not match:
                            format_error = f"Safe format error {line}"
                            break
                        dependency = match.group("dependency")
                        current_path["safe_info"] = {"dependency": dependency}
                    
                    if status == "Bug":
                        if self.bug_type == "MLK":
                            bug_pattern = r"- Dependency: (?P<dependency>.+)"
                            match = re.search(bug_pattern, line)
                            if not match:
                                format_error = f"Bug format error {line}"
                                break
                            dependency = match.group("dependency")
                            current_path["bug_info"] = {"dependency": dependency}
                        
                        if self.bug_type == "NPD" or self.bug_type == "UAF":
                            bug_pattern = r"- (Lines|Line) (?P<line>\d+)\. Trigger Operation: `(?P<deference_operation>[^`]+)`\. Dependency: (?P<dependency>.+)"
                            match = re.search(bug_pattern, line)
                            if not match:
                                format_error = f"Bug format error {line}"
                                break
                            bug_line = match.group('line')
                            operation = match.group('deference_operation')
                            dependency = match.group('dependency')
                            current_path["bug_info"] = {"operation": operation, "dependency": dependency, "line": bug_line}

                    if status == "Unknown":
                        if "propagation_info" not in current_path:
                            current_path["propagation_info"] = []
                        if line.startswith("- Callee"):
                            match = re.search(self.callee_pattern, line)
                            if not match:
                                format_error = f"Callee format error {line}"
                                break
                            callee_name = match.group('callee')
                            index = match.group('argument')
                            dependency = match.group('dependency')
                            callsite_line = match.group('line_number')
                            current_path["propagation_info"].append({"type": "Argument", "function_name": callee_name, "index": index, "dependency": dependency, "line": callsite_line})

                        if line.startswith("- Caller"):
                            match = re.search(self.caller_pattern, line)
                            if not match:
                                format_error = f"Caller format error {line}"
                                break
                            type = match.group('type')
                            index = match.group('index')
                            dependency = match.group('dependency')
                            ret_line = match.group('line_number')
                            current_path["propagation_info"].append({"type": type, "function_name": "", "index": index, "dependency": dependency, "line": ret_line})

            if format_error != "":
                print(format_error)
                continue
        return result, query_info

    def fetch_system_role(self):
        with open(self.prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        role = dump_config_dict["system_role"].replace("<LANGUAGE>", self.language)
        return role
    
    def extract_key_points_in_Cpp(self, function:Function, bug_type:str) -> List[Value]:
        """
        Extract key points from the function, including return site, invocation site and bug related site:
        Memory Leak: memory deletion sites
        Null Pointer Dereference: pointer dereference sites 
        Use after free: pointer usage sites
        """
        source_code = function.function_code
        function_node = function.parse_tree_root_node
        nodes = find_nodes_by_type(function_node, "return_statement")
        nodes.extend(find_nodes_by_type(function_node, "call_expression"))
        nodes.extend(find_nodes_by_type(function_node, "method_invocation"))
        nodes.extend(find_nodes_by_type(function_node, "parameter_declaration"))
        lines = []
        if bug_type == "MLK":
            nodes.extend(find_nodes_by_type(function_node, "delete_expression"))
            for node in nodes:
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte : node.end_byte]
                lines.append(Value(name, line_number, ValueLabel.SINK, function.file_name))
        if bug_type == "NPD":
            nodes.extend(find_nodes_by_type(function_node, "pointer_expression"))
            nodes.extend(find_nodes_by_type(function_node, "field_expression"))
            nodes.extend(find_nodes_by_type(function_node, "subscript_expression"))
            for node in nodes:
                if node.type == "pointer_expression" and node.children[0].type != "*":
                    continue
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte : node.end_byte]
                lines.append(Value(name, line_number, ValueLabel.SINK, function.file_name))
        if bug_type == "UAF":
            nodes.extend(find_nodes_by_type(function_node, "pointer_expression"))
            nodes.extend(find_nodes_by_type(function_node, "field_expression"))
            nodes.extend(find_nodes_by_type(function_node, "delete_expression"))
            for node in nodes:
                if node.type == "pointer_expression" and node.children[0].type != "*":
                    continue
                line_number = source_code[: node.start_byte].count("\n") + 1
                name = source_code[node.start_byte : node.end_byte]
                lines.append(Value(name, line_number, ValueLabel.SINK, function.file_name))
        return lines

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
        if self.language == "Cpp":
            key_points = self.extract_key_points_in_Cpp(function, self.bug_type)
        else:
            return ""
        if not key_points:
            return ""
        for key_point in key_points:
            key_point_info_template += f"- Line {key_point.line_number}: {key_point.name}\n"
        return key_point_info_template
