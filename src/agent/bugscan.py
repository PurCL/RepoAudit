import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm

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
from llmtool.bugscan.slice_bug_detector import *
from llmtool.utility.audit_request_formulator import *

from memory.semantic.bugscan_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *

from ui.logger import *

BASE_PATH = Path(__file__).resolve().parents[2]


class BugScanAgent(Agent):
    def __init__(
        self,
        project_path,
        language,
        ts_analyzer,
        model_name,
        temperature,
        call_depth,
        is_inlined=False,
        max_neural_workers=1,
        agent_id: int = 0,
        include_test_files: bool = False,
    ) -> None:
        self.project_path = project_path
        self.project_name = project_path.split("/")[-1]
        self.language = language if language not in {"C", "Cpp"} else "Cpp"
        self.ts_analyzer = ts_analyzer

        self.model_name = model_name
        self.temperature = temperature

        self.call_depth = call_depth
        self.is_inlined = is_inlined

        self.max_neural_workers = max_neural_workers
        self.MAX_QUERY_NUM = 5

        self.lock = threading.Lock()
        self.time_str = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())

        self.include_test_files = include_test_files

        with self.lock:
            self.log_dir_path = f"{BASE_PATH}/log/bugscan/{self.model_name}/{self.language}/{self.project_name}/{self.time_str}-{agent_id}"
            if not os.path.exists(self.log_dir_path):
                os.makedirs(self.log_dir_path)
            self.logger = Logger(self.log_dir_path + "/" + "bugscan.log")
            self.logger.print_console(
                f"The log directory of BugScanAgent is {self.log_dir_path}"
            )

        # LLM tools used by BugScanAgent
        self.audit_request_formulator = AuditRequestFormulator(
            "gpt-4.1-nano",
            self.temperature,
            self.language,
            self.MAX_QUERY_NUM,
            self.logger,
        )
        self.slice_inliner = SliceInliner(
            self.model_name,
            self.temperature,
            self.language,
            self.MAX_QUERY_NUM,
            self.logger,
        )

        # LLM Agent instances created by BugScanAgent
        self.slice_scan_agents: List[SliceScanAgent] = []

        # Initialize the bug specific llm tools and result files
        self.audit_request_output, self.target_files = self.formulate_audit_request()
        self.bug_type = self.audit_request_output.bug_type
        self.slice_detector = SliceBugDetector(
            self.bug_type,
            self.model_name,
            self.temperature,
            self.language,
            self.MAX_QUERY_NUM,
            self.logger,
        )

        with self.lock:
            self.res_dir_path = f"{BASE_PATH}/result/bugscan/{self.model_name}/{self.bug_type}/{self.language}/{self.project_name}/{self.time_str}-{agent_id}"
            if not os.path.exists(self.res_dir_path):
                os.makedirs(self.res_dir_path)

        # Initialize the seeds
        self.seeds: List[Tuple[Value, bool]] = self.__obtain_extractor().extract_all(
            include_test_files=self.include_test_files
        )
        self.logger.print_log(
            f"Extracted {len(self.seeds)} seeds from the code base. The seeds are as follows:"
        )
        for seed_value, is_backward in self.seeds:
            self.logger.print_log(f"Seed: {seed_value}, is_backward: {is_backward}")

        # Initialize the state
        self.state = BugScanState(self.seeds)
        return

    def formulate_audit_request(self) -> Tuple[AuditRequestFormulatorOutput, List[str]]:
        self.logger.print_console("Please enter your analysis request:")

        is_valid_input = False
        while True:
            sys.stdout.write(">>> ")
            sys.stdout.flush()
            user_prompt_str = sys.stdin.readline().strip()
            if user_prompt_str == "":
                self.logger.print_console("User prompt is empty")
                raise RAValueError("User prompt is empty")
            audit_input = AuditRequestFormulatorInput(user_prompt_str)
            audit_request_output: AuditRequestFormulatorOutput = (
                self.audit_request_formulator.invoke(audit_input)
            )
            if (
                audit_request_output is not None
                and audit_request_output.bug_type is not None
            ):
                target_files = []
                if audit_request_output.scope.type == "FileLevel":
                    for file_path in audit_request_output.scope.file_paths:
                        full_file_path = os.path.join(self.project_path, file_path)
                        if not os.path.isfile(full_file_path):
                            self.logger.print_console(
                                f"File {full_file_path} does not exist."
                            )
                            break
                        else:
                            self.logger.print_log(
                                f"Add file {full_file_path} as an analysis target."
                            )
                            target_files.append(full_file_path)
                    is_valid_input = True
                elif audit_request_output.scope.type == "DirectoryLevel":
                    for dir_path in audit_request_output.scope.directory_paths:
                        full_dir_path = os.path.join(self.project_path, dir_path)
                        if not os.path.isdir(full_dir_path):
                            self.logger.print_console(
                                f"Directory {full_dir_path} does not exist."
                            )
                            break
                        else:
                            self.logger.print_log(
                                f"Add directory {full_dir_path} as an analysis target."
                            )
                            target_files.extend(
                                [
                                    os.path.join(full_dir_path, file)
                                    for file in os.listdir(full_dir_path)
                                ]
                            )
                    is_valid_input = True
                elif audit_request_output.scope.type == "RepoLevel":
                    self.logger.print_log(
                        f"Analyze the whole repository {self.project_path}."
                    )
                    target_files = self.ts_analyzer.code_in_files
                    is_valid_input = True

            if is_valid_input:
                break

            self.logger.print_console(
                "Please specify valid relative paths of files or directories and bug types."
            )
            self.logger.print_console("RepoAudit can support the following bug types:")
            self.logger.print_console("- Null Pointer Dereference")
            self.logger.print_console("- Memory Leak")
            self.logger.print_console("- Buffer Overflow")
            self.logger.print_console("- Use After Free")
            self.logger.print_console("Please describe your auditing request again:")
        return audit_request_output, target_files

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

    def __retrieve_slice_inliner_inputs(
        self, slicescan_state: SliceScanState
    ) -> List[SliceInlinerInput]:
        inputs = []

        self.logger.print_console("start to retrieve slice inliner inputs")

        root_function_ids = []
        for relevant_function_id in slicescan_state.relevant_functions:
            relevant_function = slicescan_state.relevant_functions[relevant_function_id]
            is_root_function = True
            if (
                relevant_function.function_id
                in self.ts_analyzer.function_callee_caller_map
            ):
                for caller_function_id in self.ts_analyzer.function_callee_caller_map[
                    relevant_function.function_id
                ]:
                    if caller_function_id in slicescan_state.relevant_functions:
                        is_root_function = False
                        break
            if is_root_function:
                root_function_ids.append(relevant_function_id)

        self.logger.print_console("root functions obtained")

        for root_function_id in root_function_ids:
            relevant_function_ids = [root_function_id]
            function_caller_callee_map = {}
            while True:
                new_added_function_ids = []
                for function_id in relevant_function_ids:
                    callees = self.ts_analyzer.get_all_callee_functions(
                        self.ts_analyzer.function_env[function_id]
                    )
                    for callee in callees:
                        if callee.function_id not in slicescan_state.relevant_functions:
                            continue
                        if callee.function_id not in relevant_function_ids:
                            new_added_function_ids.append(callee.function_id)
                if len(new_added_function_ids) == 0:
                    break
                else:
                    relevant_function_ids.extend(new_added_function_ids)

            for function_caller_id in relevant_function_ids:
                if (
                    function_caller_id
                    not in self.ts_analyzer.function_caller_callee_map
                ):
                    continue
                for function_callee_id in self.ts_analyzer.function_caller_callee_map[
                    function_caller_id
                ]:
                    if function_callee_id not in relevant_function_ids:
                        continue
                    if function_caller_id not in function_caller_callee_map:
                        function_caller_callee_map[function_caller_id] = set()
                    function_caller_callee_map[function_caller_id].add(
                        function_callee_id
                    )

            slice_items = []
            for _, function_id, values, slice in slicescan_state.intra_slices:
                slice_items.append((function_id, values, slice))

            relevant_functions = {
                function_id: self.ts_analyzer.function_env[function_id]
                for function_id in relevant_function_ids
            }

            input = SliceInlinerInput(
                root_function_id,
                relevant_functions,
                slice_items,
                function_caller_callee_map,
            )
            inputs.append(input)
        return inputs

    # TOBE deprecated
    def start_scan_sequential(self) -> None:
        self.logger.print_console("Start bug scanning...")

        self.seeds_in_scope = []
        for seed_value, is_backward in self.seeds:
            if seed_value.file in self.target_files:
                self.seeds_in_scope.append((seed_value, is_backward))

        self.state.update_seed_values_in_scope(self.seeds_in_scope)

        # Process each seed sequentially with a progress bar
        with tqdm(
            total=len(self.seeds_in_scope), desc="Processing Seeds", unit="seed"
        ) as pbar:
            for seed_value, is_backward in self.seeds_in_scope:
                seed_function = self.ts_analyzer.get_function_from_localvalue(
                    seed_value
                )
                if seed_function is None:
                    pbar.update(1)
                    continue

                # (Key Step I): Start a slicescan agent for each seed
                slice_scan_agent = SliceScanAgent(
                    [seed_value],
                    is_backward,
                    self.project_path,
                    self.language,
                    self.ts_analyzer,
                    self.model_name,
                    self.temperature,
                    self.call_depth,
                    self.max_neural_workers,
                )
                self.slice_scan_agents.append(slice_scan_agent)

                slice_scan_agent.start_scan()
                slice_scan_state = slice_scan_agent.get_agent_state()

                # Obtain all the inliner instances
                slice_inliner_inputs: List[
                    SliceInlinerInput
                ] = self.__retrieve_slice_inliner_inputs(slice_scan_state)

                if self.is_inlined:
                    # Inline each instance to obtain the abstraction of buggy code snippets
                    for slice_inliner_input in slice_inliner_inputs:
                        # (Key Step II): Inline the slices
                        slice_inliner_output: SliceInlinerOutput = (
                            self.slice_inliner.invoke(slice_inliner_input)
                        )

                        if slice_inliner_output is None:
                            self.logger.print_log("Slice inliner output is None")
                            continue

                        # (Key Step III): Detect the bugs upon the inlined slices
                        intra_detector_input = SliceBugDetectorInput(
                            seed_value.name,
                            slice_inliner_output.inlined_snippet,
                            slice_inliner_input.tree_str,
                            True,
                        )
                        intra_detector_output: SliceBugDetectorOutput = (
                            self.slice_detector.invoke(intra_detector_input)
                        )

                        if intra_detector_output is None:
                            self.logger.print_log("Intra detector output is None")
                            continue

                        if intra_detector_output.is_buggy:
                            # Construct the bug report and update the state
                            explanation = (
                                "Call tree: \n"
                                + slice_inliner_input.tree_str
                                + "\n"
                                + "After the abstraction, we have the following code snippet:\n"
                                + slice_inliner_output.inlined_snippet
                                + "\n"
                                + intra_detector_output.explanation_str
                            )
                            bug_report = BugReport(
                                self.bug_type,
                                seed_value,
                                slice_inliner_input.relevant_functions,
                                explanation,
                            )
                            self.state.update_bug_report(bug_report)
                else:
                    # Do not inline the slices. Detect multiple functions with the guidance of the call trees.
                    call_tree_str = ""
                    for slice_inliner_input in slice_inliner_inputs:
                        call_tree_str += slice_inliner_input.tree_str + "\n"
                    code_str = ""
                    for _, function_id, values, slice in slice_scan_state.intra_slices:
                        code_str += slice + "\n"

                    inter_detector_input = SliceBugDetectorInput(
                        seed_value.name, code_str, call_tree_str, False
                    )
                    inter_detector_output: SliceBugDetectorOutput = (
                        self.slice_detector.invoke(inter_detector_input)
                    )

                    if inter_detector_output is None:
                        self.logger.print_log("Inter detector output is None")
                        continue

                    if inter_detector_output.is_buggy:
                        # Construct the bug report and update the state
                        explanation = (
                            "Call tree: \n"
                            + call_tree_str
                            + "\n"
                            + "After the abstraction, we have the following code snippet:\n"
                            + code_str
                            + "\n"
                            + inter_detector_output.explanation_str
                        )
                        bug_report = BugReport(
                            self.bug_type,
                            seed_value,
                            slice_inliner_input.relevant_functions,
                            explanation,
                        )
                        self.state.update_bug_report(bug_report)

                # Dump bug reports
                bug_report_dict = {
                    bug_report_id: bug.to_dict()
                    for bug_report_id, bug in self.state.bug_reports.items()
                }
                with open(
                    self.res_dir_path + "/detect_info.json", "w"
                ) as bug_info_file:
                    json.dump(bug_report_dict, bug_info_file, indent=4)

                # Update the progress bar
                pbar.update(1)

        # Final summary
        total_bug_number = len(self.state.bug_reports)
        self.logger.print_console(
            f"{total_bug_number} bug(s) was/were detected in total."
        )
        self.logger.print_console(
            f"The bug report(s) has/have been dumped to {self.res_dir_path}/detect_info.json"
        )
        self.logger.print_console("The log files are as follows:")
        for log_file in self.get_log_files():
            self.logger.print_console(log_file)
        return

    def start_scan(self) -> None:
        self.logger.print_console("Start bug scanning...")

        # Process each seed in parallel with a progress bar
        self.seeds_in_scope = []
        for seed_value, is_backward in self.seeds:
            if seed_value.file in self.target_files:
                self.seeds_in_scope.append((seed_value, is_backward))

        self.state.update_seed_values_in_scope(self.seeds_in_scope)

        with tqdm(
            total=len(self.seeds_in_scope), desc="Processing Seeds", unit="seed"
        ) as pbar:
            with ThreadPoolExecutor(max_workers=self.max_neural_workers) as executor:
                futures = [
                    executor.submit(self.__process_seed, seed_value, is_backward, index)
                    for index, (seed_value, is_backward) in enumerate(
                        self.seeds_in_scope
                    )
                ]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.print_log("Error processing seed:", e)
                    finally:
                        pbar.update(
                            1
                        )  # Update the progress bar after each seed is processed

        # Final summary
        total_bug_number = len(self.state.bug_reports)
        self.logger.print_console(
            f"{total_bug_number} bug(s) was/were detected in total."
        )
        self.logger.print_console(
            f"The bug report(s) has/have been dumped to {self.res_dir_path}/detect_info.json"
        )
        self.logger.print_console("The log files are as follows:")
        for log_file in self.get_log_files():
            self.logger.print_console(log_file)
        return

    def __process_seed(
        self, seed_value: Value, is_backward: bool, seed_index: int
    ) -> None:
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
            self.max_neural_workers,
            seed_index,
        )
        self.slice_scan_agents.append(slice_scan_agent)

        slice_scan_agent.start_scan()
        slice_scan_state = slice_scan_agent.get_agent_state()

        # Obtain all the inliner instances.
        slice_inliner_inputs: List[
            SliceInlinerInput
        ] = self.__retrieve_slice_inliner_inputs(slice_scan_state)
        self.logger.print_console("slice_inliner_inputs obtained")

        if self.is_inlined:
            # Process slice_inliner_inputs in parallel
            with ThreadPoolExecutor(max_workers=self.max_neural_workers) as executor:
                futures = [
                    executor.submit(
                        self.__process_slice_inliner_input,
                        slice_inliner_input,
                        seed_value,
                    )
                    for slice_inliner_input in slice_inliner_inputs
                ]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.print_log(
                            f"Error processing slice inliner input: {str(e)}"
                        )
        else:
            # Do not inline the slices. Detect multiple functions with the guidance of the call trees.
            call_tree_str = ""
            for slice_inliner_input in slice_inliner_inputs:
                call_tree_str += slice_inliner_input.tree_str + "\n"
            code_str = ""
            for _, function_id, values, slice in slice_scan_state.intra_slices:
                code_str += slice + "\n"

            inter_detector_input = SliceBugDetectorInput(
                seed_value.name, code_str, call_tree_str, False
            )
            inter_detector_output: SliceBugDetectorOutput = self.slice_detector.invoke(
                inter_detector_input
            )

            if inter_detector_output is None:
                self.logger.print_log("Inter detector output is None")
                return

            if inter_detector_output.is_buggy:
                # Construct the bug report and update the state
                explanation = (
                    "Call tree: \n"
                    + call_tree_str
                    + "\n"
                    + "After the abstraction, we have the following code snippet:\n"
                    + code_str
                    + "\n"
                    + inter_detector_output.explanation_str
                )
                bug_report = BugReport(
                    self.bug_type,
                    seed_value,
                    slice_inliner_input.relevant_functions,
                    explanation,
                )
                self.state.update_bug_report(bug_report)
                bug_report_dict = {
                    bug_report_id: bug.to_dict()
                    for bug_report_id, bug in self.state.bug_reports.items()
                }
                with open(
                    self.res_dir_path + "/detect_info.json", "w"
                ) as bug_info_file:
                    json.dump(bug_report_dict, bug_info_file, indent=4)

        return

    def __process_slice_inliner_input(
        self, slice_inliner_input: SliceInlinerInput, seed_value: Value
    ) -> None:
        # Inline the slices.
        slice_inliner_output: SliceInlinerOutput = self.slice_inliner.invoke(
            slice_inliner_input
        )

        if slice_inliner_output is None:
            self.logger.print_log("Slice inliner output is None")
            return

        # Detect bugs upon the inlined slices.
        intra_detector_input = SliceBugDetectorInput(
            seed_value.name,
            slice_inliner_output.inlined_snippet,
            slice_inliner_input.tree_str,
            True,
        )
        intra_detector_output: SliceBugDetectorOutput = self.slice_detector.invoke(
            intra_detector_input
        )

        if intra_detector_output is None:
            self.logger.print_log("Intra detector output is None")
            return

        if intra_detector_output.is_buggy:
            # Construct the bug report and update the state
            explanation = (
                "Call tree: \n"
                + slice_inliner_input.tree_str
                + "\n"
                + "After the abstraction, we have the following code snippet:\n"
                + slice_inliner_output.inlined_snippet
                + "\n"
                + intra_detector_output.explanation_str
            )
            bug_report = BugReport(
                self.bug_type,
                seed_value,
                slice_inliner_input.relevant_functions,
                explanation,
            )

            # Use lock to safely update shared state and write to file
            self.state.update_bug_report(bug_report)
            bug_report_dict = {
                bug_report_id: bug.to_dict()
                for bug_report_id, bug in self.state.bug_reports.items()
            }
            with open(self.res_dir_path + "/detect_info.json", "w") as bug_info_file:
                json.dump(bug_report_dict, bug_info_file, indent=4)
        return

    def get_agent_state(self) -> BugScanState:
        return self.state

    def get_log_files(self) -> List[str]:
        log_files = []
        log_files.append(self.log_dir_path + "/" + "bugscan.log")
        for slice_scan_agent in self.slice_scan_agents:
            log_files.append(slice_scan_agent.log_dir_path + "/" + "slicescan.log")
        return log_files
