import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from agent.agent import *
from agent.slicescan import *

from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *

from tstool.bugscan_extractor.bugscan_extractor import *
from tstool.bugscan_extractor.Cpp.Cpp_BOF_extractor import *
from tstool.bugscan_extractor.Cpp.Cpp_MLK_extractor import *
from tstool.bugscan_extractor.Cpp.Cpp_NPD_extractor import *
from tstool.bugscan_extractor.Cpp.Cpp_UAF_extractor import *
from tstool.bugscan_extractor.Go.Go_BOF_extractor import *
from tstool.bugscan_extractor.Go.Go_NPD_extractor import *
from tstool.bugscan_extractor.Java.Java_NPD_extractor import *
from tstool.bugscan_extractor.Python.Python_NPD_extractor import *

from llmtool.LLM_utils import *
from llmtool.bugscan.slice_inliner import *
from llmtool.bugscan.intra_detector import *

from memory.semantic.bugscan_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *

from pathlib import Path
BASE_PATH = Path(__file__).resolve().parents[2]


class BugScanAgent(Agent):
    def __init__(self,
                 bug_type,
                 project_path,
                 language,
                 ts_analyzer,
                 model_name,
                 temperature,
                 call_depth,
                 max_workers=1
                 ) -> None:
        self.bug_type = bug_type

        self.project_path = project_path
        self.project_name = project_path.split("/")[-1]
        self.language = language if language not in {"C", "Cpp"} else "Cpp"
        self.ts_analyzer = ts_analyzer

        self.model_name = model_name
        self.temperature = temperature
        
        self.call_depth = call_depth
        self.max_workers = max_workers
        self.MAX_QUERY_NUM = 5

        self.log_dir_path = f"{BASE_PATH}/log/bugscan-{self.model_name}/{self.language}-{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.log_dir_path):
            os.makedirs(self.log_dir_path)

        self.result_dir_path = f"{BASE_PATH}/result/bugscan-{self.model_name}/{self.language}-{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.result_dir_path):
            os.makedirs(self.result_dir_path)

        # LLM tools used by BugScanAgent
        self.slice_inliner = SliceInliner(self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM)
        self.intra_detector = IntraDetector(self.bug_type, self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM)

        # LLM Agent instances created by BugScanAgent
        self.SliceScanAgent: List[SliceScanAgent] = []

        self.seeds: List[Tuple[Value, bool]] = self.__obtain_extractor().extract_all()
        self.state = BugScanState(self.seeds)

        self.file_lock = threading.Lock()
        return
    
    def __obtain_extractor(self) -> BugScanExtractor:
        if self.language == "Cpp":
            if self.bug_type == "BOF":
                return Cpp_BOF_Extractor(self.ts_analyzer)
            elif self.bug_type == "MLK":
                return Cpp_MLK_Extractor(self.ts_analyzer)
            elif self.bug_type == "NPD":
                return Cpp_NPD_Extractor(self.ts_analyzer)
            elif self.bug_type == "UAF":
                return Cpp_UAF_Extractor(self.ts_analyzer)
        elif self.language == "Go":
            if self.bug_type == "BOF":
                return Go_BOF_Extractor(self.ts_analyzer)
            elif self.bug_type == "NPD":
                return Go_NPD_Extractor(self.ts_analyzer)
        elif self.language == "Java":
            if self.bug_type == "NPD":
                return Java_NPD_Extractor(self.ts_analyzer)
        elif self.language == "Python":
            if self.bug_type == "NPD":
                return Python_NPD_Extractor(self.ts_analyzer)
        # TODO: otherwise, sythesize the extractor
        return None


    def __retrieve_slice_inliner_inputs(self, slicescan_state: SliceScanState) -> List[SliceInlinerInput]:
        inputs = []

        print("start to retrieve slice inliner inputs")

        root_function_ids = []
        for relevant_function_id in slicescan_state.relevant_functions:
            relevant_function = slicescan_state.relevant_functions[relevant_function_id]
            is_root_function = True
            if relevant_function.function_id in self.ts_analyzer.function_callee_caller_map:
                for caller_function_id in self.ts_analyzer.function_callee_caller_map[relevant_function.function_id]:
                    if caller_function_id in slicescan_state.relevant_functions:
                        is_root_function = False
                        break
            if is_root_function:
                root_function_ids.append(relevant_function_id)

        for root_function_id in root_function_ids:
            callees = self.ts_analyzer.get_all_transitive_callee_functions(self.ts_analyzer.function_env[root_function_id], 2 * self.call_depth + 2)
            
            relevant_functions = {
                callee.function_id: callee
                for callee in callees
                if callee.function_id in slicescan_state.relevant_functions
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

    # TOBE deprecated
    def start_scan_sequential(self) -> None:
        print("Start bug scanning...")

        # Analyze each seed value, which is potential buggy point or root cause
        for (seed_value, is_backward) in self.seeds:
            seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
            if seed_function == None:
                continue

            # (Key Step I): Start a slicescan agent for each seed
            slice_scan_agent = SliceScanAgent([seed_value], is_backward, self.project_path, \
                                              self.language, self.ts_analyzer, \
                                              self.model_name, self.temperature, self.call_depth, self.max_workers)
            self.SliceScanAgent.append(slice_scan_agent)

            slice_scan_agent.start_scan()
            slice_scan_state = slice_scan_agent.get_agent_state()

            # Obtain all the inliner instances
            slice_inliner_inputs: List[SliceInlinerInput] = self.__retrieve_slice_inliner_inputs(slice_scan_state)

            # Inline each instance to obtain the abstraction of buggy code snippets (consisting of slices in the relevant functions)
            for slice_inliner_input in slice_inliner_inputs:
                # (Key Step II): Inline the slices
                slice_inliner_output: SliceInlinerOutput = self.slice_inliner.invoke(slice_inliner_input)

                if slice_inliner_output is None:
                    print("Slice inliner output is None")
                    continue

                # (Key Step III): Detect the bugs upon the inlined slices
                intra_detector_input = IntraDetectorInput(seed_value.name, slice_inliner_output.inlined_snippet)
                intra_detector_output: IntraDetectorOutput = self.intra_detector.invoke(intra_detector_input)

                if intra_detector_output is None:
                    print("Intra detector output is None")
                    continue

                # Construct the bug report and update the state
                explanation = "Call tree: \n" + slice_inliner_input.tree_str + "\n" \
                                + "After the abstraction, we have the following code snippet:\n" \
                                + slice_inliner_output.inlined_snippet + "\n" \
                                + intra_detector_output.explanation_str
                bug_report = BugReport(self.bug_type, seed_value, slice_inliner_input.relevant_functions, explanation)
                self.state.update_state(bug_report)

            # Dump bug reports
            bug_report_dict = {bug_report_id: bug.to_dict() for bug_report_id, bug in self.state.bug_reports.items()}
            with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
                json.dump(bug_report_dict, bug_info_file, indent=4)

            total_bug_number = len(self.state.bug_reports)
            print(f"{total_bug_number} bug(s) was/were detected in total.")
            print(f"The bug report(s) has/have been dumped to {self.result_dir_path}/detect_info.json")
        return
    
    def start_scan(self) -> None:
        print("Start bug scanning...")
    
        # Process each seed in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self.__process_seed, seed_value, is_backward)
                for (seed_value, is_backward) in self.seeds
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print("Error processing seed:", e)

        # Final summary
        total_bug_number = len(self.state.bug_reports)
        print(f"{total_bug_number} bug(s) was/were detected in total.")
        print(f"The bug report(s) has/have been dumped to {self.result_dir_path}/detect_info.json")
        return

    def __process_seed(self, seed_value: Value, is_backward: bool) -> None:
        seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
        if seed_function is None:
            return

        # (Key Step I): Start a slicescan agent for the seed.
        slice_scan_agent = SliceScanAgent(
            [seed_value],
            is_backward,
            self.project_path,
            self.language,
            self.ts_analyzer,
            self.model_name,
            self.temperature,
            self.call_depth,
            self.max_workers
        )
        self.SliceScanAgent.append(slice_scan_agent)

        slice_scan_agent.start_scan()
        slice_scan_state = slice_scan_agent.get_agent_state()

        # Obtain all the inliner instances.
        slice_inliner_inputs: List[SliceInlinerInput] = self.__retrieve_slice_inliner_inputs(slice_scan_state)

        # (Key Step II & III): Inline each instance and run intra detection to generate bug reports.
        for slice_inliner_input in slice_inliner_inputs:
            # Inline the slices.
            slice_inliner_output: SliceInlinerOutput = self.slice_inliner.invoke(slice_inliner_input)

            if slice_inliner_output is None:
                print("Slice inliner output is None")
                continue

            # Detect bugs upon the inlined slices.
            intra_detector_input = IntraDetectorInput(seed_value.name, slice_inliner_output.inlined_snippet)
            intra_detector_output: IntraDetectorOutput = self.intra_detector.invoke(intra_detector_input)

            if intra_detector_output is None:
                print("Intra detector output is None")
                continue

            # Construct the bug report and update the state.
            explanation = (
                "Call tree: \n" + slice_inliner_input.tree_str + "\n" +
                "After the abstraction, we have the following code snippet:\n" +
                slice_inliner_output.inlined_snippet + "\n" +
                intra_detector_output.explanation_str
            )
            bug_report = BugReport(self.bug_type, seed_value, slice_inliner_input.relevant_functions, explanation)
            self.state.update_state(bug_report)

        # Write to detect_info.json for the current seed. Use lock to protect the file during writes.
        with self.file_lock:
            bug_report_dict = {bug_report_id: bug.to_dict() for bug_report_id, bug in self.state.bug_reports.items()}
            with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
                json.dump(bug_report_dict, bug_info_file, indent=4)
        
    def get_agent_state(self) -> BugScanState:
        return self.state
