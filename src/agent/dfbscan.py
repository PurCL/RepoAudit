import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *

from tstool.dfbscan_extractor.dfbscan_extractor import *
from tstool.dfbscan_extractor.Cpp.Cpp_MLK_extractor import *
from tstool.dfbscan_extractor.Cpp.Cpp_NPD_extractor import *
from tstool.dfbscan_extractor.Cpp.Cpp_UAF_extractor import *

from llmtool.LLM_utils import *
from llmtool.DF_analyzer import *
from llmtool.DF_validator import *

from memory.semantic.dfa_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *

BASE_PATH = Path(__file__).resolve().parents[2]

class Trace:
    def __init__(self, explanation: str, src_name: str, src_line: int, function_name: str, function_code: str, file_name: str):
        self.explanation = explanation
        self.src_name = src_name
        self.src_line = src_line
        self.function_name = function_name
        self.function_code = function_code
        self.file_name = file_name


class DFBScanAgent:
    def __init__(self,
                 project_name,
                 language,
                 all_files,
                 inference_model_name,
                 temperature,
                 bug_type,
                 boundary,
                 max_workers=6
                 ) -> None:
        self.project_name = project_name
        self.language = language if language not in {"C", "Cpp"} else "Cpp"
        self.all_files = all_files
        self.model_name = inference_model_name
        self.temperature = temperature
        self.bug_type = bug_type
        self.boundary = boundary
        self.max_workers = max_workers
        
        self.detection_result = []
        if self.language == "Cpp":
            self.ts_analyzer = Cpp_TSAnalyzer(self.all_files, self.language)
        elif self.language == "Go":
            self.ts_analyzer = Go_TSAnalyzer(self.all_files, self.language)
        elif self.language == "Java":
            self.ts_analyzer = Java_TSAnalyzer(self.all_files, self.language)
        elif self.language == "Python":
            self.ts_analyzer = Python_TSAnalyzer(self.all_files, self.language)
        else:
            print("Unsupported language")
            exit(1)
        
        self.df_analyzer = DataflowAnalyzer(
            self.model_name, 
            temperature,
            self.language, 
            self.ts_analyzer,
            self.boundary,
            self.bug_type
        )

        self.validator = DataFlowValidator(
            self.model_name,
            temperature,
            language,
            self.bug_type
        )

        self.run_info = {}
        self.bug_info = {}
        self.vali_info = {}
        self.vali_result = {}
        self.bug_num = 0

        self.result_dir_path = f"{BASE_PATH}/result/dfbscan-{self.model_name}/{self.bug_type}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.result_dir_path):
            os.makedirs(self.result_dir_path)

        self.src_values, self.sink_values = self.__obtain_extractor().extract_all()
        # DEBUG
        print("=" * 100)
        print("Source Values: ", len(self.src_values))
        for src_value in self.src_values:
            print(src_value.name, src_value.line_number)
        print("=" * 100)
    
    def __obtain_extractor(self) -> DFBScanExtractor:
        if self.language == "Cpp":
            if self.bug_type == "MLK":
                return Cpp_MLK_Extractor(self.ts_analyzer)
            elif self.bug_type == "NPD":
                return Cpp_NPD_Extractor(self.ts_analyzer)
            elif self.bug_type == "UAF":
                return Cpp_UAF_Extractor(self.ts_analyzer)
        elif self.language == "Python":
            pass
        elif self.language == "Go":
            pass
        # TODO: otherwise, sythesize the extractor
        return None

    def start_scan(self):
        print("Start dataflow scanning...")
        
        
        def sequential():
            # Start to analyze each source
            for src_value in tqdm(self.src_values, desc="Processing Source Values", unit="src"):
                src_function = self.ts_analyzer.get_function_from_localvalue(src_value)
                if src_function == None:
                    continue
                
                # Construct an analysis state and retrieve callers/callees during forward/backward slicing
                src_state = DFAState(src_value, src_function)
                flag, run_info_list = self.df_analyzer.analyze(src_state, 0)

                # flag: whether the LLM format is valid or not.
                # Slices are generated if flag is True.
                if not flag:
                    continue

                # Detect the bugs upon slices using LLM (inlining enabled)
                key = src_state.get_key()
                self.run_info[key] = run_info_list
                
                bug_tace_list = self.find_bug_trace(src_state)

                if len(bug_tace_list) > 0:
                    for bug_trace in bug_tace_list:
                        key = " --> ".join([f"({path.src_name}, {path.function_name})" for path in bug_trace])
                        if key not in self.bug_info.keys():
                            vali_result, vali_info = self.validate_with_LLM(bug_trace)
                            self.vali_result[key] = "True" if vali_result else "False"
                            self.vali_info[key] = vali_info
                            if self.vali_result[key] == "True":
                                self.bug_num += 1
                                self.bug_info[key] = {
                                    "Explanation": [path.explanation for path in bug_trace],
                                    "Path": [],
                                    "Vali_human": ""
                                }
                                for path in bug_trace:
                                    path_info = {
                                        "source": path.src_name,
                                        "src_line": path.src_line,
                                        "function_name": path.function_name,
                                        "function_code": path.function_code,
                                        "file_name": path.file_name,
                                    }
                                    self.bug_info[key]["Path"].append(path_info)

            with open(f"{self.result_dir_path}/bug_info.json", "w") as f:
                json.dump(self.bug_info, f, indent=4)
            
            with open(f"{self.result_dir_path}/run_info.json", "w") as f:
                json.dump(self.run_info, f, indent=4)
        
            with open(f"{self.result_dir_path}/vali_info.json", "w") as f:
                json.dump(self.vali_info, f, indent=4)

            print("="*100)
            print("Finish Path scan...")
            print("Bug Number: ", self.bug_num)
            print("Qurey Number: ", self.df_analyzer.query_num)
            print("Input Token Cost: ", self.df_analyzer.total_input_token_cost)
            print("Output Token Cost: ", self.df_analyzer.total_output_token_cost)


        def parallel(n):
            lock = threading.Lock()
            
            def worker(src_value):
                src_function = self.ts_analyzer.get_function_from_localvalue(src_value)
                if src_function is None:
                    return

                # Construct an analysis state and retrieve callers/callees during forward/backward slicing
                src_state = DFAState(src_value, src_function)
                flag, run_info_list = self.df_analyzer.analyze(src_state, 0)

                # flag: whether the LLM format is valid or not.
                # Slices are generated if flag is True.
                if not flag:
                    return

                # Detect the bugs upon slices using LLM (inlining enabled)
                key = src_state.get_key()
                self.run_info[key] = run_info_list

                bug_tace_list = self.find_bug_trace(src_state)

                if len(bug_tace_list) > 0:
                    for bug_trace in bug_tace_list:
                        key = " --> ".join([f"({path.src_name}, {path.function_name})" for path in bug_trace])
                        if key not in self.bug_info.keys():
                            vali_result, vali_info = self.validate_with_LLM(bug_trace)
                            self.vali_result[key] = "True" if vali_result else "False"
                            self.vali_info[key] = vali_info
                            if self.vali_result[key] == "True":
                                self.bug_num += 1
                                self.bug_info[key] = {
                                    "Explanation": [path.explanation for path in bug_trace],
                                    "Path": [],
                                    "Vali_human": ""
                                }
                                for path in bug_trace:
                                    path_info = {
                                        "source": path.src_name,
                                        "src_line": path.src_line,
                                        "function_name": path.function_name,
                                        "function_code": path.function_code,
                                        "file_name": path.file_name,
                                    }
                                    self.bug_info[key]["Path"].append(path_info)

                # Use lock to protect file writes
                with lock:
                    with open(f"{self.result_dir_path}/bug_info.json", "w") as f:
                        json.dump(self.bug_info, f, indent=4)
                    
                    with open(f"{self.result_dir_path}/run_info.json", "w") as f:
                        json.dump(self.run_info, f, indent=4)
                
                    with open(f"{self.result_dir_path}/vali_info.json", "w") as f:
                        json.dump(self.vali_info, f, indent=4)

            # Process at most n src concurrently
            with tqdm(total=len(self.src_values), desc="Processing Source Values", unit="src") as pbar:
                with ThreadPoolExecutor(max_workers=n) as executor:
                    futures = [executor.submit(worker, src_value) for src_value in self.src_values]
                    for future in as_completed(futures):
                        # Could log exceptions here if needed
                        try:
                            future.result()
                        except Exception as e:
                            print(f"Error processing src: {e}")
                        finally:
                            pbar.update(1)
            
        if self.max_workers == 1:
            sequential()
        else:
            parallel(self.max_workers)


    def find_bug_trace(self, state: DFAState) -> list[list[Trace]]:
        """
        Postprocess the state, return true if the state has a buggy path
        """
        bug_trace_list = []
        def find_bug_trace(state: DFAState, trace_list: list[Trace], bug_path_list: list[list[Trace]], depth: int) -> None:
            """
            Postprocess the state, return true if the state has a buggy path
            """
            if depth > self.boundary:
                return
            for subpath in state.subpath:
                print(subpath.get_status())
                if subpath.get_status() == "Bug":
                    # add trace info to the bug trace
                    bug_trace = []
                    for trace in trace_list:
                        bug_trace.append(trace)
                    src_line = state.function.file_line2function_line(state.var.line_number)
                    bug_trace.append(Trace(explanation = subpath.dependency, src_name = state.var.name, src_line = src_line, function_name = state.function.function_name, function_code = state.function.function_code, file_name = state.function.file_name))
                    bug_path_list.append(bug_trace)
                    continue

                if subpath.get_status() == "Safe":
                    continue

                if subpath.get_status() == "Unknown":
                    for (child_state, dependency, _) in subpath.children:
                        src_line = state.function.file_line2function_line(state.var.line_number)
                        child_trace = Trace(explanation = dependency, src_name = state.var.name, src_line = src_line, function_name = state.function.function_name, function_code = state.function.function_code, file_name = state.function.file_name)
                        # add trace info to the path trace
                        trace_list.append(child_trace)
                        find_bug_trace(child_state, trace_list, bug_path_list, depth + 1)
                        trace_list.pop()
            return
        find_bug_trace(state, [], bug_trace_list, 0)
        return bug_trace_list


    def validate_with_LLM(self, bug_trace:list[Trace]) -> Tuple[bool, dict]:
        vali_paths = []
        for i, path in enumerate(bug_trace):
            vali_paths.append(f"`{path.src_name}` at line {path.src_line} in the function `{path.function_name}`")
        vali_path = " --> ".join(vali_paths)

        lined_explanation = ""
        for i, path in enumerate(bug_trace):
            lined_explanation += f"{i+1}. {path.explanation}\n"

        function_body = "\n\n".join([f"```{path.function_code}```" for path in bug_trace])

        return self.validator.validate(vali_path, lined_explanation, function_body)
