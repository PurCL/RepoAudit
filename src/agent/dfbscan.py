import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *

from tstool.dfbscan_extractor.dfbscan_extractor import *
from tstool.dfbscan_extractor.Cpp.Cpp_MLK_extractor import *
from tstool.dfbscan_extractor.Cpp.Cpp_NPD_extractor import *
from tstool.dfbscan_extractor.Cpp.Cpp_UAF_extractor import *
from tstool.dfbscan_extractor.Java.Java_NPD_extractor import *

from llmtool.LLM_utils import *
from llmtool.intra_dfa import *
from llmtool.path_validator import *

from memory.semantic.dfb_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *

from pathlib import Path
BASE_PATH = Path(__file__).resolve().parents[2]


class DFBScanAgent:
    def __init__(self,
                 bug_type,
                 is_reachable,
                 project_path,
                 language,
                 ts_analyzer,
                 model_name,
                 temperature,
                 call_depth,
                 max_workers=1
                 ) -> None:
        self.bug_type = bug_type
        self.is_reachable = is_reachable
        
        self.project_path = project_path
        self.language = language if language not in {"C", "Cpp"} else "Cpp"
        self.ts_analyzer = ts_analyzer

        self.model_name = model_name
        self.temperature = temperature
        
        self.call_depth = call_depth
        self.max_workers = max_workers
        self.MAX_QUERY_NUM = 5

        self.project_name = project_path.split("/")[-1]
        self.log_dir_path = f"{BASE_PATH}/log/dfbscan-{self.model_name}/{self.language}-{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.log_dir_path):
            os.makedirs(self.log_dir_path)

        self.result_dir_path = f"{BASE_PATH}/result/dfbscan-{self.model_name}/{self.language}-{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.result_dir_path):
            os.makedirs(self.result_dir_path)

        # LLM tools used by DFBScanAgent
        self.intra_dfa = IntraDataFlowAnalyzer(self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM)
        self.path_validator = PathValidator(self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM)

        self.src_values, self.sink_values = self.__obtain_extractor().extract_all()
        self.state = DFBState(self.src_values, self.sink_values)
        return
        

    def __obtain_extractor(self) -> DFBScanExtractor:
        if self.language == "Cpp":
            if self.bug_type == "MLK":
                return Cpp_MLK_Extractor(self.ts_analyzer)
            elif self.bug_type == "NPD":
                return Cpp_NPD_Extractor(self.ts_analyzer)
            elif self.bug_type == "UAF":
                return Cpp_UAF_Extractor(self.ts_analyzer)
        elif self.language == "Java":
            if self.bug_type == "NPD":
                return Java_NPD_Extractor(self.ts_analyzer)
        elif self.language == "Python":
            pass
        elif self.language == "Go":
            pass
        # TODO: otherwise, sythesize the extractor
        return None
    

    def __collect_potential_buggy_paths(self, 
                                        current_value: Value, 
                                        call_context: CallContext,
                                        path_with_unknown_status: List[Value] = [],
                                        paths_with_buggy_status: List[List[Value]] = []) -> List[List[Value]]:
        if current_value not in self.reachable_values_per_path:
            # source must reach sink, e.g., memory leak
            if self.is_reachable:
                paths_with_buggy_status.append(path_with_unknown_status)
            return paths_with_buggy_status
        
        reachable_values_paths: List[Set[Value]] = self.reachable_values_per_path[current_value]

        for value in reachable_values_paths:
            if value.label == ValueLabel.SINK:
                # source must not reach sink, e.g., null pointer dereference
                if not self.is_reachable:
                    paths_with_buggy_status.append(path_with_unknown_status + [value])
            elif value.label in {ValueLabel.PARA, ValueLabel.RET, ValueLabel.ARG, ValueLabel.OUT}:
                current_function = self.ts_analyzer.get_function_from_localvalue(value)

                if value.label == ValueLabel.PARA:
                    # TODO: convert the value from para to arg. Model side-effect
                    pass
                if value.label == ValueLabel.RET:
                    # convert the value from return to output value
                    output_function_context_list = self.ts_analyzer.get_output_values_by_return_value_in_call_context(current_function, call_context)
                    for (output_value, caller_function, new_context) in output_function_context_list:
                        self.__collect_potential_buggy_paths(output_value, new_context, path_with_unknown_status + [value, output_value], paths_with_buggy_status)
                if value.label == ValueLabel.ARG:
                    # convert the value from arg to para
                    para_function_context_list = self.ts_analyzer.get_parameters_by_argument_in_call_context(value, current_function, call_context)
                    for (para_value, callee_function, new_context) in para_function_context_list:
                        self.__collect_potential_buggy_paths(para_value, new_context, path_with_unknown_status + [value, para_value], paths_with_buggy_status)
                    pass
                if value.label == ValueLabel.OUT:
                    # TODO: convert the value from output value to return
                    pass
        return paths_with_buggy_status


    def start_scan(self) -> None:
        print("Start data-flow bug scanning...")

        for src_value in self.src_values:
            worklist = []
            src_function = self.ts_analyzer.get_function_from_localvalue(src_value)
            if src_function is None:
                continue
        
            worklist.append((src_value, src_function, 0))
            while len(worklist) > 0:
                (start_value, start_function, depth) = worklist.pop(0)
                if depth > self.call_depth:
                    continue

                # construct the input for intra-procedural data-flow analysis
                sinks_in_function = self.__obtain_extractor().extract_sinks(start_function)
                sink_values = [(sink.name, sink.line_number - start_function.start_line_number + 1) for sink in sinks_in_function]

                call_statements = []
                for call_site_node in start_function.function_call_site_nodes:
                    file_content = self.ts_analyzer.code_in_files[start_function.file_path]
                    call_site_line_number = file_content[: call_site_node.start_byte].count("\n") + 1
                    call_site_name = file_content[call_site_node.start_byte: call_site_node.end_byte]
                    call_statements.append((call_site_name, call_site_line_number))

                ret_values = [(ret.name, ret.line_number - start_function.start_line_number + 1) for ret in start_function.retvals]
                input = IntraDataFlowAnalyzerInput(start_function, start_value, sink_values, call_statements, ret_values)
            
                # invoke the intra-procedural data-flow analysis
                output = self.intra_dfa.invoke(input)
                for end_values in output.reachable_values:
                    for end_value in end_values:
                        end_function = self.ts_analyzer.get_function_from_localvalue(end_value)
                        if end_function is None:
                            continue
                        worklist.append((end_value, end_function, depth + 1))
                self.state.update_reachable_values_per_path(start_value, Set(output.reachable_values))

            buggy_paths: List[List[Value]] = self.__collect_potential_buggy_paths(src_value, CallContext(False))

            for buggy_path in buggy_paths:
                input = PathValidatorInput(buggy_path, {value: self.ts_analyzer.get_function_from_localvalue(value) for value in buggy_path})
                output: PathValidatorOutput = self.path_validator.invoke(input)
                if output.is_reachable:
                    print(f"Potential bug found: {output.poc_str}")

                    relevant_functions = []
                    for value in buggy_path:
                        function = self.ts_analyzer.get_function_from_localvalue(value)
                        if function is not None:
                            relevant_functions[function.function_id] = function

                    bug_report = BugReport(self.bug_type, src_value, relevant_functions, output.poc_str)
                    self.state.update_bug_reports(src_value, bug_report)
            
            # Dump bug reports
            bug_report_dict = {bug_report_id: bug.to_dict() for bug_report_id, bug in self.state.bug_reports.items()}
            with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
                json.dump(bug_report_dict, bug_info_file, indent=4)
        return


    def get_agent_result(self) -> DFBState:
        return self.state
