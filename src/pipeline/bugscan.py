import json
import os
from parser.response_parser import *
from parser.program_parser import *
from parser.ts_transform import *
from utility.llm import *
from utility.df_state import *
from utility.function import *
from utility.localvalue import *
from LMAgent.df_validator import DataFlowValidator
from LMAgent.df_analyzer import DataflowAnalyzer
from pathlib import Path

class PostPath:
    def __init__(self, path, explanation, function_path, status="", src_line:int = 0, sink_line:int = 0, function_id:int = 0, function_name:str = "", src_name:str = ""):
        self.path = path
        self.explanation = explanation
        self.function_path = function_path
        self.status = status
        self.src_line = src_line
        self.sink_line = sink_line
        self.function_id = function_id
        self.function_name = function_name
        self.src_name = src_name


class BugScanPipeline:
    def __init__(self,
                 src_spec_file,
                 sink_spec_file,
                 analyze_prompt_file,
                 validate_prompt_file,
                 project_name,
                 language,
                 all_files,
                 inference_model_name,
                 temperature,
                 is_fscot,
                 bug_type,
                 sink_functions,
                 boundary=3):
        self.src_spec_file = src_spec_file
        self.sink_spec_file = sink_spec_file
        self.analyze_prompt_file = analyze_prompt_file
        self.validate_prompt_file = validate_prompt_file
        self.project_name = project_name
        self.language = language
        self.all_files = all_files
        self.bug_type = bug_type
        self.boundary = boundary
        self.sink_functions = sink_functions
        self.model_name = inference_model_name

        self.detection_result = []
        self.ts_analyzer = TSAnalyzer(self.all_files, self.language)
        self.function_processor = TSFunctionProcessor(self.ts_analyzer, self.language)
        self.df_analyzer = DataflowAnalyzer(
            self.analyze_prompt_file, 
            self.model_name, 
            temperature, 
            self.language, 
            self.ts_analyzer, 
            self.function_processor, 
            is_fscot,
            self.boundary,
            self.bug_type,
            self.sink_functions
            )
        
        bug_type_map = {
            "NPD": "Null Pointer Dereference",
            "UAF": "Use After Free",
            "ML": "Memory Leak",
        }
        self.validator = DataFlowValidator(
            prompt_file=self.validate_prompt_file,
            model_name=self.model_name,
            temp=0.0,
            language=language,
            bug_type=bug_type_map[bug_type],
        )

    def start_scan(self):
        """
        Scan 
        """
        log_dir_path = str(
            Path(__file__).resolve().parent.parent.parent / (f"log/{self.bug_type}/{self.project_name}")
        )
        if not os.path.exists(log_dir_path):
            os.makedirs(log_dir_path)
        
        # result_dir_path = str(
        #     Path(__file__).resolve().parent.parent.parent / (f"result-gpt4/{self.bug_type}/{self.project_name}")
        # )

        # result_dir_path = str(
        #     Path(__file__).resolve().parent.parent.parent / (f"result-LLM-validate/{self.bug_type}/{self.project_name}")
        # )

        result_dir_path = str(
            Path(__file__).resolve().parent.parent.parent / (f"result-{self.model_name}/{self.bug_type}/{self.project_name}")
        )

        if not os.path.exists(result_dir_path):
            os.makedirs(result_dir_path)

        print("Start Path scan...")
        src_lines = []
        with open (self.src_spec_file, "r") as f:
            src_spec = json.load(f)
        for src in src_spec:
            src_lines.append(LocalValue.from_string(src))
        
        self.sink_lines = []
        with open (self.sink_spec_file, "r") as f:
            sink_spec = json.load(f)
        for sink in sink_spec:
            self.sink_lines.append(LocalValue.from_string(sink))

        bug_report_file = open(result_dir_path + "/bug_report.json", 'w')
        self.bug_report = {}
        self.run_info = {}
        self.vali_result = {}

        for src in src_lines:
            self.df_analyzer.result_list = []
            
            src_function = self.ts_analyzer.get_function_from_localvalue(src)
            if src_function == None:
                continue
            key = (src.line_number, src_function.function_name)

            print("\n\n")
            print(src)
            src_state = self.df_analyzer.search(src, src_function, 0)
            if src_state == None:
                continue
            self.run_info[str(key)] = self.df_analyzer.result_list
            
            self.bug_path_list: list[list[PostPath]] = []

            if self.bug_type == "ML":
                self.unreach_postprocess(src_state, [], 0)
                # filter the safe pathes: we only conclude a path as ML bug when all sub-pathes don't release the memory
                print("Before Filter:", len(self.bug_path_list))
                temp_bug_path_list = []
                for bug_trace in self.bug_path_list:
                    bug = True
                    print("Path Status:")
                    for path in bug_trace:
                        if path.status == "Safe":
                            bug = False
                            break
                    if bug:
                        temp_bug_path_list.append(bug_trace)
                self.bug_path_list = temp_bug_path_list
                print("After Filter:", len(self.bug_path_list))
            else:
                self.reach_postprocess(src_state, [], 0)

            if len(self.bug_path_list) > 0:
                for bug_trace in self.bug_path_list:
                    path = " --> ".join([path.path for path in bug_trace])
                    explanation = "\n".join([path.explanation for path in bug_trace])
                    function_path = " --> ".join([path.function_path for path in bug_trace])
                    src_sink_path = " --> ".join([f"<Name:{path.function_name}, ID:{path.function_id}, SRC:{path.src_line}, SINK:{path.sink_line}>" for path in bug_trace])

                    # LLM validate
                    if function_path not in self.vali_result:
                        self.vali_result[function_path] = "TP" if self.validate_with_LLM(bug_trace) else "FP"

                    if function_path not in self.bug_report.keys():
                        self.bug_report[function_path] = []
                    self.bug_report[function_path].append({"Path": path, "Explanation": explanation, "SrcSinkPath": src_sink_path, "Validate": self.vali_result[function_path]})

        bug_report_file.write(json.dumps(self.bug_report, indent=4))

        bug_report_file.close()

        with open(result_dir_path + "/run_info.json", 'w') as run_info_file:
            json.dump(self.run_info, run_info_file, indent=4)

        print("="*100)
        print("Finish Path scan...")
        print("Bug Number: ", len(self.bug_report))
        print("Qurey Number: ", self.df_analyzer.query_num)
        print("Input Token Cost: ", self.df_analyzer.input_token_cost)
        print("Output Token Cost: ", self.df_analyzer.output_token_cost)


    def unreach_postprocess(self, state: State, path_trace: list[PostPath], depth: int) -> bool:
        """
        Postprocess the state, return true if the state has a buggy path
        """
        if depth > self.boundary:
            return False
        is_buggy = False
        for subpath in state.subpath:
            if subpath.get_status() == "Bug":
                bug_trace: list[PostPath] = []
                # add path info to the bug trace
                for path in path_trace:
                    bug_trace.append(path)
                bug_trace.append(PostPath(str(subpath), subpath.dependency, subpath.state.get_key(), "Bug", src_line = state.source.line_number, sink_line = 0, function_id = state.function.function_id, function_name = state.function.function_name, src_name = state.source.name))
                self.bug_path_list.append(bug_trace)
                is_buggy = True
                continue

            if subpath.get_status() == "Safe":
                continue

            if subpath.get_status() == "Unknown":
                children_path_list = []
                status = "Unknown"
                for (child_state, dependency, type, sink_line) in subpath.children:
                    src_line = state.source.line_number
                    if type == "pointer parameter":
                        sink_line = 0
                    else:
                        reachability = TSAnalyzer.check_control_reachability(state.function, src_line, sink_line)
                        if not reachability:
                            print(f"Unreachable: Function {state.function.function_name}. {src_line} -> {sink_line} Path: {state.function.file_name}")
                            continue
                    child_path = PostPath(str(subpath), dependency, subpath.state.get_key(), "Unknown", src_line = src_line, sink_line = sink_line, function_id = state.function.function_id, function_name = state.function.function_name, src_name = state.source.name)
                    children_path_list.append(child_path)
                    # add path info to the path trace
                    path_trace.append(child_path)
                    child_bug = self.unreach_postprocess(child_state, path_trace, depth + 1)
                    path_trace.pop()
                    if not child_bug and type == "callee":
                        status = "Safe"
                if status == "Safe":
                    for child_path in children_path_list:
                        child_path.status = "Safe"
                else:
                    is_buggy = True
        if is_buggy:
            return True
        return False
    
    
    def reach_postprocess(self, state: State, path_trace: list[PostPath], depth: int):
        """
        Postprocess the state, return true if the state has a buggy path
        """
        if depth > self.boundary:
            return
        for subpath in state.subpath:
            print(subpath.get_status())
            if subpath.get_status() == "Bug":
                if self.bug_type == "NPD":
                    if not subpath.sink or not self.validate_sink(subpath.sink):
                        continue
                if self.bug_type == "UAF":
                    if not subpath.sink:
                        continue
                bug_trace = []
                # add path info to the bug trace
                for path in path_trace:
                    bug_trace.append(path)
                src_line = state.source.line_number
                sink_line = subpath.sink.line_number
                reachability = TSAnalyzer.check_control_reachability(state.function, src_line, sink_line)
                if not reachability:
                    print(f"Unreachable: Function {state.function.function_name}. {src_line} -> {sink_line} Path: {state.function.file_name}")
                    continue
                bug_trace.append(PostPath(str(subpath), subpath.dependency, subpath.state.get_key(), "Bug", src_line = src_line, sink_line = sink_line, function_id = state.function.function_id, function_name = state.function.function_name, src_name = state.source.name))
                self.bug_path_list.append(bug_trace)
                continue

            if subpath.get_status() == "Safe":
                continue

            if subpath.get_status() == "Unknown":
                for (child_state, dependency, type, sink_line) in subpath.children:
                    src_line = state.source.line_number
                    if type == "pointer parameter":
                        sink_line = 0
                    else:
                        reachability = TSAnalyzer.check_control_reachability(state.function, src_line, sink_line)
                        if not reachability:
                            print(f"Unreachable: Function {state.function.function_name}. {src_line} -> {sink_line} Path: {state.function.file_name}")
                            continue
                    child_path = PostPath(str(subpath), dependency, subpath.state.get_key(), "Unknown", src_line = src_line, sink_line = sink_line, function_id = state.function.function_id, function_name = state.function.function_name, src_name = state.source.name)
                    # add path info to the path trace
                    path_trace.append(child_path)
                    self.reach_postprocess(child_state, path_trace, depth + 1)
                    path_trace.pop()
        return
    

    def validate_sink(self, sink_point: LocalValue) -> bool:
        """
        Validate the sink
        """
        for sink in self.sink_lines:
            if sink.line_number == sink_point.line_number and sink.file == sink_point.file:
                return True
        return False


    def validate_with_LLM(self, bug_trace) -> bool:
        functions = [self.ts_analyzer.environment[path.function_id] for path in bug_trace]
        
        vali_paths = []
        for i, path in enumerate(bug_trace):
            vali_paths.append(f"`{path.src_name}` at line {functions[i].file_line2function_line(int(path.src_line))} in the function `{functions[i].function_name}`")
        vali_path = " --> ".join(vali_paths)

        lined_explanation = ""
        for i, path in enumerate(bug_trace):
            lined_explanation += f"{i+1}. {path.explanation}\n"

        function_body = ""
        for function in functions:
            if not function.lined_code_without_comments:
                self.function_processor.transform(function.function_code)
                function.lined_code_without_comments = self.function_processor.lined_code_without_comments
            function_body += function.lined_code_without_comments + "\n\n"

        return self.validator.validate_with_LLM(vali_path, lined_explanation, function_body)