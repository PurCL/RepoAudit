import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *
from llmtool.LLM_utils import *
from memory.semantic.bugscan_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *
from agent.slicescan import *
from llmtool.slice_inliner import *
from llmtool.intra_detector import *
from pathlib import Path
BASE_PATH = Path(__file__).resolve().parents[2]


class BugScanAgent:
    def __init__(self,
                 seed_spec_file,
                 bug_type,
                 project_name,
                 language,
                 code_in_files,
                 inference_model_name,
                 temperature,
                 call_depth,
                 max_workers=1
                 ) -> None:
        self.seed_spec_file = seed_spec_file
        self.bug_type = bug_type

        self.project_name = project_name
        self.language = language if language not in {"C", "Cpp"} else "Cpp"
        self.code_in_files = code_in_files

        self.model_name = inference_model_name
        self.temperature = temperature
        
        self.call_depth = call_depth
        self.max_workers = max_workers
        self.MAX_QUERY_NUM = 5

        self.log_dir_path = f"{BASE_PATH}/log/bugscan-{self.model_name}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.log_dir_path):
            os.makedirs(self.log_dir_path)

        self.result_dir_path = f"{BASE_PATH}/result/bugscan-{self.model_name}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.result_dir_path):
            os.makedirs(self.result_dir_path)

        if self.language == "Cpp":
            self.ts_analyzer = Cpp_TSAnalyzer(self.code_in_files, self.language)
        elif self.language == "Go":
            self.ts_analyzer = Go_TSAnalyzer(self.code_in_files, self.language)
        elif self.language == "Java":
            self.ts_analyzer = Java_TSAnalyzer(self.code_in_files, self.language)
        elif self.language == "Python":
            self.ts_analyzer = Python_TSAnalyzer(self.code_in_files, self.language)
        else:
            print("Unsupported language")
            exit(1)

        # LLM tools used by BugScanAgent
        self.slice_inliner = SliceInliner(self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM)
        self.intra_detector = IntraDetector(self.bug_type, self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM)

        # LLM Agent instances created by BugScanAgent
        self.SliceScanAgent: List[SliceScanAgent] = []

        self.seeds = self.__load_seed_from_file()
        self.state = BugScanState(self.seeds)
        return
    

    def __load_seed_from_file(self) -> List[Tuple[Value, bool]]:
        """
        :return: a list of seed-bool pairs, indicating the seed value and the direction of slicing
        """
        seeds = []
        with open (self.seed_spec_file, "r") as f:
            seed_spec = json.load(f)
        for seed_str in seed_spec:
            try:
                if seed_str.strip("\n").endswith(" 1"):
                    is_backward = True
                    seed_value = Value.from_str_to_value(seed_str.replace("\n", "").strip(" 1"))
                elif seed_str.strip("\n").endswith(" 0"):
                    is_backward = False
                    seed_value = Value.from_str_to_value(seed_str.replace("\n", "").strip(" 0"))
            except:
                print(f"Error parsing seed: {seed_str}")
                print("Skip this seed")
                continue
            seeds.append((seed_value, is_backward))
        return seeds
    
    
    def __retrieve_slice_inliner_inputs(self, slicescan_state: SliceScanState) -> List[SliceInlinerInput]:
        inputs = []

        print("start to retrieve slice inliner inputs")

        root_function_ids = []
        for relevant_function_id in slicescan_state.relevant_functions:
            relevant_function = slicescan_state.relevant_functions[relevant_function_id]
            print("relevenat function name: ", relevant_function.function_name)
            is_root_function = True
            if relevant_function.function_id in self.ts_analyzer.function_callee_caller_map:
                for caller_function_id in self.ts_analyzer.function_callee_caller_map[relevant_function.function_id]:
                    if caller_function_id in slicescan_state.relevant_functions:
                        is_root_function = False
                        break
            if is_root_function:
                print("root function: ", self.ts_analyzer.function_env[relevant_function_id].function_name)
                root_function_ids.append(relevant_function_id)

        for root_function_id in root_function_ids:
            callee_ids = self.ts_analyzer.get_all_transitive_callee_functions(self.ts_analyzer.function_env[root_function_id])
            
            relevant_functions = {
                callee_id: self.ts_analyzer.function_env[callee_id]
                for callee_id in callee_ids
                if callee_id in slicescan_state.relevant_functions
            }
            relevant_functions[root_function_id] = self.ts_analyzer.function_env[root_function_id]

            
            slice_items = []
            for (_, function_id, values, slice) in slicescan_state.intra_slices:
                slice_items.append((function_id, values, slice))

            function_caller_callee_map = {}
            for function_caller_id in self.ts_analyzer.function_caller_callee_map:
                if function_caller_id not in relevant_functions:
                    continue
                for function_callee_id in self.ts_analyzer.function_caller_callee_map[function_caller_id]:
                    if function_callee_id not in relevant_functions:
                        continue
                    if function_caller_id not in function_caller_callee_map:
                        function_caller_callee_map[function_caller_id] = set()
                    function_caller_callee_map[function_caller_id].add(function_callee_id)

            input = SliceInlinerInput(root_function_id, relevant_functions, slice_items, function_caller_callee_map)
            inputs.append(input)
        return inputs


    def start_scan(self) -> None:
        print("Start bug scanning...")

        # Analyze each seed value, which is potential buggy point or root cause
        for (seed_value, is_backward) in self.seeds:
            seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
            if seed_function == None:
                continue

            # (Key Step I): Start a slicescan agent for each seed
            slice_scan_agent = SliceScanAgent([seed_value], is_backward, self.project_name, \
                                              self.language, self.code_in_files, \
                                              self.model_name, self.temperature, self.call_depth, self.max_workers)
            self.SliceScanAgent.append(slice_scan_agent)

            slice_scan_agent.start_scan()
            slice_scan_state = slice_scan_agent.get_agent_state()

            # Obtain all the inliner instances
            slice_inliner_inputs: List[SliceInlinerInput] = self.__retrieve_slice_inliner_inputs(slice_scan_state)

            print("#slice_inliner_inputs: ", len(slice_inliner_inputs))
            for slice_inliner_input in slice_inliner_inputs:
                print(slice_inliner_input.tree_str)


            # Inline each instance to obtain the abstraction of buggy code snippets (consisting of slices in the relevant functions)
            for slice_inliner_input in slice_inliner_inputs:
                # (Key Step II): Inline the slices
                slice_inliner_output: SliceInlinerOutput = self.slice_inliner.invoke(slice_inliner_input)

                # (Key Step III): Detect the bugs upon the inlined slices
                intra_detector_input = IntraDetectorInput(seed_value.name, slice_inliner_output.inlined_snippet)
                intra_detector_output: IntraDetectorOutput = self.intra_detector.invoke(intra_detector_input)

                # Construct the bug report and update the state
                explanation = "After the abstraction, we have the following code snippet:\n" \
                                + slice_inliner_output.inlined_snippet + "\n" \
                                + intra_detector_output.poc_str
                bug_report = BugReport(self.bug_type, seed_value, slice_inliner_input.relevant_functions, explanation)
                self.state.update_state(bug_report)
                print(str(bug_report))

            # Dump bug reports
            bug_report_dict = {bug_report_id: bug.to_dict() for bug_report_id, bug in self.state.bug_reports.items()}
            with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
                json.dump(bug_report_dict, bug_info_file, indent=4)

        # def sequential():
        #     # Start to analyze each seed
        #     for (seed_value, is_backward) in seeds:
        #         seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
        #         if seed_function == None:
        #             continue
                
        #         # Construct an analysis state and retrieve callers/callees during forward/backward slicing
        #         seed_state = BugScanState(seed_value, seed_function)
        #         if is_backward:
        #             flag = self.forward_slicing_analyzer.analyze(seed_state, 0)
        #         else:
        #             flag = self.backward_slicing_analyzer.analyze(seed_state, 0)

        #         # flag: whether the LLM format is valid or not.
        #         # Slices are generated if flag is True.
        #         if not flag:
        #             continue

        #         # Detect the bugs upon slices using LLM (inlining enabled)
        #         key = seed_state.get_key()
        #         if is_backward:
        #             self.run_info[key] = self.forward_slicing_analyzer.result_list
        #         else:
        #             self.run_info[key] = self.backward_slicing_analyzer.result_list
        #         answer, poc = self.detect_with_llm(seed_state)
                
        #         # For DEBUG
        #         print("====================================")
        #         print("Is Bug: ", answer)
        #         print("PoC: ", poc)
        #         print("===============================================")

        #         # Dump bug reports
        #         with open(self.result_dir_path + "/slicing_info.json", 'w') as run_info_file:
        #             json.dump(self.run_info, run_info_file, indent=4)

        #         with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
        #             json.dump(self.bug_info, bug_info_file, indent=4)
        

        # def parallel(n):
        #     lock = threading.Lock()
            
        #     def worker(seed):
        #         (seed_value, is_forward) = seed
        #         seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
        #         if seed_function is None:
        #             return

        #         # Construct an analysis state and retrieve callers/callees during forward/backward slicing
        #         seed_state = BugScanState(seed_value, seed_function)
        #         if is_forward:
        #             flag = self.forward_slicing_analyzer.analyze(seed_state, 0)
        #         else:
        #             flag = self.backward_slicing_analyzer.analyze(seed_state, 0)

        #         # flag: whether the LLM format is valid or not.
        #         # Slices are generated if flag is True.
        #         if not flag:
        #             return

        #         # Detect the bugs upon slices using LLM (inlining enabled)
        #         key = seed_state.get_key()
        #         if is_forward:
        #             self.run_info[key] = self.forward_slicing_analyzer.result_list
        #         else:
        #             self.run_info[key] = self.backward_slicing_analyzer.result_list
        #         answer, poc = self.detect_with_llm(seed_state)

        #         # For DEBUG
        #         print("====================================")
        #         print("Is Bug: ", answer)
        #         print("PoC: ", poc)
        #         print("===============================================")

        #         # Use lock to protect file writes
        #         with lock:
        #             with open(self.result_dir_path + "/slicing_info.json", 'w') as run_info_file:
        #                 json.dump(self.run_info, run_info_file, indent=4)
        #             with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
        #                 json.dump(self.bug_info, bug_info_file, indent=4)

        #     # Process at most n src concurrently
        #     with ThreadPoolExecutor(max_workers=n) as executor:
        #         futures = [executor.submit(worker, seed) for seed in seeds]
        #         for future in as_completed(futures):
        #             # Could log exceptions here if needed
        #             try:
        #                 future.result()
        #             except Exception as e:
        #                 print(f"Error processing src: {e}")
        
        # if self.max_workers == 1:
        #     sequential()
        # else:
        #     parallel(self.max_workers)
        
    def get_agent_result(self) -> BugScanState:
        return self.state
