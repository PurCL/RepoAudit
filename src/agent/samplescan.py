import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm

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
from llmtool.samplescan.seed_selector import *
from llmtool.bugscan.slice_inliner import *
from llmtool.samplescan.function_bug_detector import *

from agent.agent import *
from agent.slicescan import *

from memory.semantic.samplescan_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *

from ui.logger import Logger

BASE_PATH = Path(__file__).resolve().parents[2]


seed_locations = {
    "cpv-1": "((*u, ../benchmark/Cpp/cpv-1/src/http/ngx_http_request.c, 4091, -1), ValueLabel.BUF_ACCESS_EXPR) 0",
    "cpv-2": "((*d++, ../benchmark/Cpp/cpv-2/src/core/ngx_string.c, 1281, -1), ValueLabel.BUF_ACCESS_EXPR) 0",
    "cpv-3": "((*b->last++, ../benchmark/Cpp/cpv-3/src/http/ngx_http_request.c, 4092, -1), ValueLabel.BUF_ACCESS_EXPR) 0",
    "cpv-4": "((ngx_sprintf(browser_cookie->value.data, \"\\\"%xT-%xO\\\":%s\",\n                                  r->headers_out.last_modified_time,\n                                  r->headers_out.content_length_n,\n                                  r->headers_in.cookie->value.data), ../benchmark/Cpp/cpv-4/src/http/ngx_http_core_module.c, 5289, -1), ValueLabel.BUF_ACCESS_EXPR) 0",
    "cpv-5": "((ngx_get_con_his(r->connection_history, r->request_counter), ../benchmark/Cpp/cpv-5/src/http/ngx_http_variables.c, 2757, -1), ValueLabel.NON_BUF_ACCESS_EXPR) 1",
    "cpv-8": "((ngx_memcpy(s->login.data, arg[0].data, s->login.len), ../benchmark/Cpp/cpv-8/src/mail/ngx_mail_pop3_handler.c, 324, -1), ValueLabel.BUF_ACCESS_EXPR) 0",
    "cpv-9": "((reader, ../benchmark/Cpp/cpv-9/src/core/ngx_cycle.c, 1513, -1), ValueLabel.NON_BUF_ACCESS_EXPR) 1",
    "cpv-10": "((r->headers_in.prefer, ../benchmark/Cpp/cpv-10/src/http/ngx_http_request.c, 4039, -1), ValueLabel.NON_BUF_ACCESS_EXPR) 1",
    "cpv-11": "((cycle->host_specs, ../benchmark/Cpp/cpv-11/src/core/ngx_cycle.c, 459, -1), ValueLabel.NON_BUF_ACCESS_EXPR) 1",
    "cpv-12": "((rev[j], ../benchmark/Cpp/cpv-12/src/os/unix/ngx_linux_sendfile_chain.c, 77, -1), ValueLabel.BUF_ACCESS_EXPR) 0",
    "cpv-13": "((ngx_pnalloc(c->pool, sizeof(ngx_auth_log_t)), ../benchmark/Cpp/cpv-13/src/mail/ngx_mail_pop3_handler.c, 381, -1), ValueLabel.NON_BUF_ACCESS_EXPR) 1",
    "cpv-14": "((r->uri.data[i], ../benchmark/Cpp/cpv-14/src/http/ngx_http_core_module.c, 1561, -1), ValueLabel.BUF_ACCESS_EXPR) 0",
    "cpv-15": "((src->data[len], ../benchmark/Cpp/cpv-15/src/core/ngx_string.c, 1262, -1), ValueLabel.BUF_ACCESS_EXPR) 0",
    "cpv-17": "((c, ../benchmark/Cpp/cpv-17/src/mail/ngx_mail_smtp_handler.c, 836, -1), ValueLabel.NON_BUF_ACCESS_EXPR) 1",
}

cases = {
    "cpv-1": {"Function": "ngx_http_validate_from", "File": "../benchmark/Cpp/cpv-1/src/http/ngx_http_request.c", "Type": "Buffer Overflow"},
    "cpv-2": {"Function": "ngx_decode_base64_internal", "File": "../benchmark/Cpp/cpv-2/src/core/ngx_string.c", "Type": "Buffer Overflow"},
    "cpv-3": {"Function": "ngx_http_trace_handler", "File": "../benchmark/Cpp/cpv-3/src/http/ngx_http_request.c", "Type": "Buffer Overflow"},
    "cpv-4": {"Function": "ngx_http_set_browser_cookie", "File": "../benchmark/Cpp/cpv-4/src/http/ngx_http_core_module.c", "Type": "Buffer Overflow"},
    "cpv-5": {"Function": "ngx_http_get_last_ip_variable", "File": "../benchmark/Cpp/cpv-5/src/http/ngx_http_variables.c", "Type": "Null Pointer Dereference"},
    "cpv-8": {"Function": "ngx_mail_pop3_user", "File": "../benchmark/Cpp/cpv-8/src/mail/ngx_mail_pop3_handler.c", "Type": "Buffer Overflow"},
    "cpv-9": {"Function": "ngx_black_list_remove", "File": "../benchmark/Cpp/cpv-9/src/core/ngx_cycle.c", "Type": "Use After Free"},
    "cpv-10": {"Function": "ngx_http_process_prefer", "File": "../benchmark/Cpp/cpv-10/src/http/ngx_http_request.c", "Type": "Use After Free"},
    "cpv-11": {"Function": "ngx_init_cycle", "File": "../benchmark/Cpp/cpv-11/src/core/ngx_cycle.c", "Type": "Use After Free"},
    "cpv-12": {"Function": "ngx_sendfile_r", "File": "../benchmark/Cpp/cpv-12/src/os/unix/ngx_linux_sendfile_chain.c", "Type": "Buffer Overflow"},
    "cpv-13": {"Function": "ngx_mail_pop3_pass", "File": "../benchmark/Cpp/cpv-13/src/mail/ngx_mail_pop3_handler.c", "Type": "Null Pointer Dereference"},
    "cpv-14": {"Function": "ngx_http_set_exten", "File": "../benchmark/Cpp/cpv-14/src/http/ngx_http_core_module.c", "Type": "Buffer Overflow"},
    "cpv-15": {"Function": "ngx_decode_base64_internal", "File": "../benchmark/Cpp/cpv-15/src/core/ngx_string.c", "Type": "Buffer Overflow"},
    "cpv-17": {"Function": "ngx_mail_smtp_noop", "File": "../benchmark/Cpp/cpv-17/src/mail/ngx_mail_smtp_handler.c", "Type": "Use After Free"}
}

class SampleScanAgent(Agent):
    def __init__(self,
                 project_path,
                 language,
                 ts_analyzer,
                 seed_selection_model,
                 slicing_model,
                 inlining_model,
                 function_detection_model,
                 temperature,
                 call_depth,
                 max_workers=1
                 ) -> None:

        self.project_path = project_path
        self.project_name = project_path.split("/")[-1]

        if self.project_name not in cases:
            raise ValueError(f"Project name {self.project_name} not in cases")
        
        if cases[self.project_name]["Type"] == "Buffer Overflow":
            self.bug_type = "BOF"
        elif cases[self.project_name]["Type"] == "Use After Free":
            self.bug_type = "UAF"
        elif cases[self.project_name]["Type"] == "Null Pointer Dereference":
            self.bug_type = "NPD"
        elif cases[self.project_name]["Type"] == "Memory Leak":
            self.bug_type = "MLK"
        
        self.language = language if language not in {"C", "Cpp"} else "Cpp"
        self.ts_analyzer = ts_analyzer

        self.seed_selection_model = seed_selection_model
        self.slicing_model = slicing_model
        self.inlining_model = inlining_model
        self.function_detection_model = function_detection_model
        self.temperature = temperature
        
        self.call_depth = call_depth
        self.max_workers = max_workers
        self.MAX_QUERY_NUM = 5

        self.log_dir_path = f"{BASE_PATH}/log/samplescan-{self.slicing_model}/{self.language}-{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.log_dir_path):
            os.makedirs(self.log_dir_path)
        self.logger = Logger(self.log_dir_path + "/" + "samplescan.log")

        self.result_dir_path = f"{BASE_PATH}/result/samplescan-{self.slicing_model}/{self.language}-{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.result_dir_path):
            os.makedirs(self.result_dir_path)

        # LLM tools used by SampleScanAgent
        self.seed_selector = SeedSelector(self.seed_selection_model, self.temperature, self.language, self.bug_type, self.MAX_QUERY_NUM, self.logger)
        self.slice_inliner = SliceInliner(self.inlining_model, self.temperature, self.language, self.MAX_QUERY_NUM, self.logger)
        self.intra_detector = IntraFunctionDetector(self.bug_type, self.function_detection_model, self.temperature, self.language, self.MAX_QUERY_NUM, self.logger)

        # LLM Agent instances created by SampleScanAgent
        self.SliceScanAgent: List[SliceScanAgent] = []

        self.initial_seeds: List[Tuple[Value, bool]] = self.__obtain_extractor().extract_all()
        self.sampled_seeds = []
        self.state = SampleScanState(self.sampled_seeds)

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

        self.logger.print_console("Start to retrieve slice inliner inputs")

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
            root_function = self.ts_analyzer.function_env[root_function_id]

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
    def start_scan_squential(self) -> None:
        self.logger.print_console("Start bug scanning...")
    
        # (Key Step I): Intra-procedural seed selection
        initial_seeds_in_functions = {}
        for (seed_value, is_backward) in self.initial_seeds:
            seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
            if seed_function.function_id not in initial_seeds_in_functions:
                initial_seeds_in_functions[seed_function.function_id] = []
            initial_seeds_in_functions[seed_function.function_id].append((seed_value, is_backward))

        for function_id in initial_seeds_in_functions:
            seed_function = self.ts_analyzer.function_env[function_id]
            if seed_function.function_name != cases[self.project_name]["Function"]:
                continue
            seed_list = [seed_value for (seed_value, is_backward) in initial_seeds_in_functions[function_id]]
            input = SeedSelectorInput(seed_function, seed_list)
            output = self.seed_selector.invoke(input)

            if output is None:
                continue

            for output_seed_value in output.seed_list:
                self.sampled_seeds.append((output_seed_value, is_backward))

        self.state.update_sampled_seed_values(self.sampled_seeds)
        
        # dump to log
        output_seed_value_strs = [str(output_seed_value) for (output_seed_value, is_backward) in self.sampled_seeds]
        target_seed_value_str = seed_locations[self.project_name]
        with open(self.log_dir_path + "/seed_log.txt", 'w') as seed_log_file:
            seed_log_file.write("Sampled seeds:\n")
            for output_seed_value_str in output_seed_value_strs:
                seed_log_file.write(output_seed_value_str + "\n")
            seed_log_file.write("Target seed:\n")
            seed_log_file.write(target_seed_value_str + "\n")

        # Analyze each seed value, which is potential buggy point or root cause
        for (seed_value, is_backward) in self.sampled_seeds:
            seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
            if seed_function == None:
                continue

            is_analyzed = False
            for (file_name, line_number) in self.state.bug_report_lines.values():
                if file_name == seed_value.file and line_number == seed_value.line_number:
                    is_analyzed = True
                    break
            if is_analyzed:
                return

            # (Key Step II): Start a slicescan agent for each seed
            slice_scan_agent = SliceScanAgent([seed_value], is_backward, self.project_path, \
                                              self.language, self.ts_analyzer, \
                                              self.slicing_model, self.temperature, self.call_depth, self.max_workers)
            self.SliceScanAgent.append(slice_scan_agent)

            slice_scan_agent.start_scan()
            slice_scan_state = slice_scan_agent.get_agent_state()

            # Obtain all the inliner instances
            slice_inliner_inputs: List[SliceInlinerInput] = self.__retrieve_slice_inliner_inputs(slice_scan_state)

            # Inline each instance to obtain the abstraction of buggy code snippets (consisting of slices in the relevant functions)
            for slice_inliner_input in tqdm(slice_inliner_inputs, desc="Processing Slices", unit="slice"):
                # (Key Step III): Inline the slices
                slice_inliner_output: SliceInlinerOutput = self.slice_inliner.invoke(slice_inliner_input)

                if slice_inliner_output is None:
                    self.logger.print_console("Error: No slice inlined.")
                    continue

                # (Key Step IV): Detect the bugs upon the inlined slices
                intra_function_detector_input = FunctionBugDetectorInput(slice_inliner_output.inlined_snippet)
                intra_function_detector_output: FunctionBugDetectorOutput = self.intra_detector.invoke(intra_function_detector_input)

                if intra_function_detector_output is None:
                    continue

                if intra_function_detector_output.is_buggy:
                    # Construct the bug report and update the state
                    explanation = (
                        "Call tree: \n" + slice_inliner_input.tree_str + "\n"
                        + "After the abstraction, we have the following code snippet:\n"
                        + slice_inliner_output.inlined_snippet + "\n"
                        + intra_function_detector_output.explanation_str
                    )
                    bug_report = BugReport(self.bug_type, seed_value, slice_inliner_input.relevant_functions, explanation)
                    self.state.update_state(bug_report)

            # Dump bug reports
            with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
                json.dump(self.state.bug_report_lines, bug_info_file, indent=4)
            self.logger.print_console(f"{len(self.state.bug_report_lines)} bug(s) was/were detected in total.")
            self.logger.print_console(f"The bug report(s) has/have been dumped to {self.result_dir_path}/detect_info.json")
            self.logger.print_console("The log files are as follows:")
            for log_file in self.get_log_files():
                self.logger.print_console(log_file)
        return
    

    def start_scan(self) -> None:
        self.logger.print_console("==================================")
        self.logger.print_console("Start bug scanning in parallel...")
        self.logger.print_console("==================================\n")

        # (Key Step I): Intra-procedural seed selection
        self.logger.print_console("---------------------------------------------------")
        self.logger.print_console("Step I: Start intra-procedural seed selection...")
        self.logger.print_console("---------------------------------------------------\n")
        initial_seeds_in_functions = {}
        for (seed_value, is_backward) in self.initial_seeds:
            seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
            if seed_function.function_id not in initial_seeds_in_functions:
                initial_seeds_in_functions[seed_function.function_id] = []
            initial_seeds_in_functions[seed_function.function_id].append((seed_value, is_backward))

        for function_id in initial_seeds_in_functions:
            seed_function = self.ts_analyzer.function_env[function_id]
            if seed_function.function_name != cases[self.project_name]["Function"]:
                continue
            seed_list = [seed_value for (seed_value, is_backward) in initial_seeds_in_functions[function_id]]
            input = SeedSelectorInput(seed_function, seed_list)
            output = self.seed_selector.invoke(input)

            if output is None:
                continue

            for output_seed_value in output.seed_list:
                self.sampled_seeds.append((output_seed_value, is_backward))

        self.state.update_sampled_seed_values(self.sampled_seeds)

        # Dump to log
        output_seed_value_strs = [str(output_seed_value) for (output_seed_value, is_backward) in self.sampled_seeds]
        target_seed_value_str = seed_locations[self.project_name]
        with open(self.log_dir_path + "/seed_log.txt", 'w') as seed_log_file:
            seed_log_file.write("Sampled seeds:\n")
            for output_seed_value_str in output_seed_value_strs:
                seed_log_file.write(output_seed_value_str + "\n")
            seed_log_file.write("Target seed:\n")
            seed_log_file.write(target_seed_value_str + "\n")

        # Process each seed in parallel with a progress bar
        total_seeds = len(self.sampled_seeds)
        processed_seeds = 0

        with tqdm(total=total_seeds, desc="Processing Seeds", unit="seed") as pbar:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [
                    executor.submit(self.__process_seed_parallel, seed_value, is_backward)
                    for (seed_value, is_backward) in self.sampled_seeds
                ]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.print_console("Error processing seed:", e)
                    finally:
                        processed_seeds += 1
                        pbar.update(1)  # Update the progress bar


        # Final summary
        self.logger.print_console(f"{len(self.state.bug_report_lines)} bug(s) was/were detected in total.")
        self.logger.print_console(f"The bug report(s) has/have been dumped to {self.result_dir_path}/detect_info.json")
        self.logger.print_console("The log files are as follows:")
        for log_file in self.get_log_files():
            self.logger.print_console(log_file)
        return
    

    def __process_seed_parallel(self, seed_value: Value, is_backward: bool) -> None:
        is_analyzed = False
        for (file_name, line_number) in self.state.bug_report_lines.values():
            if file_name == seed_value.file and line_number == seed_value.line_number:
                is_analyzed = True
                break
        if is_analyzed:
            return

        seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
        if seed_function is None:
            return
        
        self.logger.print_console("---------------------------------------------------")
        self.logger.print_console("Step II: Start the inter-procedural slicing...")
        self.logger.print_console("Value info: ", str(seed_value))
        self.logger.print_console("---------------------------------------------------\n")

        # (Key Step II): Start a slicescan agent for the seed
        slice_scan_agent = SliceScanAgent(
            [seed_value],
            is_backward,
            self.project_path,
            self.language,
            self.ts_analyzer,
            self.slicing_model,
            self.temperature,
            self.call_depth,
            self.max_workers
        )
        self.SliceScanAgent.append(slice_scan_agent)

        slice_scan_agent.start_scan()
        slice_scan_state = slice_scan_agent.get_agent_state()

        # Obtain all the inliner instances
        slice_inliner_inputs: List[SliceInlinerInput] = self.__retrieve_slice_inliner_inputs(slice_scan_state)

        self.logger.print_console("---------------------------------------------------")
        self.logger.print_console("Step III & IV: Start the detection upon inlined slice...")
        self.logger.print_console("Value info: ", str(seed_value))
        self.logger.print_console("slice number: ", len(slice_inliner_inputs))
        self.logger.print_console("---------------------------------------------------\n")

        # Inline each instance to obtain the abstraction of buggy code snippets
        cnt = 0
        for slice_inliner_input in slice_inliner_inputs:
            self.logger.print_console("---------------------------------------------------")
            self.logger.print_console("Step III: Start the inlining...", f"{cnt + 1}/{len(slice_inliner_inputs)}")
            self.logger.print_console("---------------------------------------------------\n")

            # (Key Step III): Inline the slices
            slice_inliner_output: SliceInlinerOutput = self.slice_inliner.invoke(slice_inliner_input)

            if slice_inliner_output is None:
                self.logger.print_console("Error: No slice inlined.")
                continue

            self.logger.print_console("---------------------------------------------------")
            self.logger.print_console("Step IV: Start the detection...", f"{cnt + 1}/{len(slice_inliner_inputs)}")
            self.logger.print_console("---------------------------------------------------\n")

            # (Key Step IV): Detect the bugs upon the inlined slices
            intra_function_detector_input = FunctionBugDetectorInput(slice_inliner_output.inlined_snippet)
            intra_function_detector_output: FunctionBugDetectorOutput = self.intra_detector.invoke(intra_function_detector_input)

            if intra_function_detector_output is None:
                continue

            if intra_function_detector_output.is_buggy:
                # Construct the bug report and update the state
                explanation = (
                    "Call tree: \n" + slice_inliner_input.tree_str + "\n"
                    + "After the abstraction, we have the following code snippet:\n"
                    + slice_inliner_output.inlined_snippet + "\n"
                    + intra_function_detector_output.explanation_str
                )
                bug_report = BugReport(self.bug_type, seed_value, slice_inliner_input.relevant_functions, explanation)
                self.state.update_state(bug_report)
            
            # Write to detect_info.json for the current seed. Use lock to protect the file during writes
            with self.file_lock:
                self.state.update_bug_report(seed_value, bug_report)
                with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
                    json.dump(self.state.bug_report_lines, bug_info_file, indent=4)


    def get_agent_state(self) -> SampleScanState:
        return self.state

    def get_log_files(self) -> List[str]:
        log_files = []
        log_files.append(self.log_dir_path + "/" + "samplescan.log")
        for slice_scan_agent in self.slice_scan_agents:
            log_files.append(slice_scan_agent.log_dir_path + "/" + "slicescan.log")
        return log_files