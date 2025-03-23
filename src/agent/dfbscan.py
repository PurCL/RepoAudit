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

        self.log_dir_path = f"{BASE_PATH}/log/dfbscan-{self.model_name}/{self.project_path}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.log_dir_path):
            os.makedirs(self.log_dir_path)

        self.result_dir_path = f"{BASE_PATH}/result/dfbscan-{self.model_name}/{self.project_path}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.result_dir_path):
            os.makedirs(self.result_dir_path)

        # LLM tools used by DFBScanAgent
        self.intra_dfa = IntraDataFlowAnalyzer(self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM)
        self.path_validator = PathValidator(self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM)

        # TODO
        self.src_values, self.sink_values = self.__load_value_from_file()
        self.state = DFBState(self.src_values, self.sink_values)
        return
        

    
    def __load_value_from_file(self) -> Tuple[List[Value], List[Value]]:
        """
        :return: two lists of values, indicating the sources or sinks in the data-flow bug detection
        """
        srcs = []
        sinks = []
        with open(self.src_spec_file, "r") as f:
            src_spec = json.load(f)
        for src_str in src_spec:
            src = Value.from_str_to_value(src_str.replace("\n", ""))
            srcs.append(src)
        
        with open(self.sink_spec_file, "r") as f:
            sink_spec = json.load(f)
        for sink_str in sink_spec:
            sink = Value.from_str_to_value(sink_str.replace("\n", ""))
            sinks.append(sink)
        return srcs, sinks
    

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
                input = IntraDataFlowAnalyzerInput(start_value, start_function)
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
