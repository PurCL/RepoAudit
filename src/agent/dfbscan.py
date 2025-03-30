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

        self.file_lock = threading.Lock()
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
    
    def __update_worklist(self, 
                        input: IntraDataFlowAnalyzerInput, 
                        output: IntraDataFlowAnalyzerOutput, 
                        call_context: CallContext,
                        path_index: int,
                        ) -> List[Tuple[Value, Function, CallContext]]:
        """
        Update the worklist based on the output of intra-procedural data-flow analysis.
        :param input: The input of intra-procedural data-flow analysis
        :param output: The output of intra-procedural data-flow analysis
        :param call_context: The call context of the current function
        :return: The updated worklist
        """
        delta_worklist = []  # The list of (value, function, call_context) tuples
        function_id = input.function.function_id
        function = self.ts_analyzer.function_env[function_id]

        for value in output.reachable_values[path_index]:
            if value.label == ValueLabel.ARG:
                callee_functions = self.ts_analyzer.get_all_callee_functions(function)
                for callee_function in callee_functions:
                    is_called = False
                    call_sites = self.ts_analyzer.get_callsites_by_callee_name(function, callee_function.function_name)
                    for call_site_node in call_sites:
                        file_content = self.ts_analyzer.code_in_files[function.file_path]
                        call_site_lower_line_number = file_content[:call_site_node.start_byte].count("\n") + 1
                        call_site_upper_line_number = file_content[:call_site_node.end_byte].count("\n") + 1
                        arg_line_number_in_file = function.start_line_number + value.line_number - 1
                        if not (call_site_lower_line_number <= arg_line_number_in_file and arg_line_number_in_file <= call_site_upper_line_number):
                            is_called = True
                    if not is_called:
                        continue
                            
                    new_call_context = copy.deepcopy(call_context)
                    is_CFL_reachable = new_call_context.add_and_check_context(callee_function.function_id, ContextLabel.LEFT_PAR)

                    # violate CFL reachability and then skip
                    if not is_CFL_reachable:
                        continue
                    
                    for para in callee_function.paras:
                        if para.index == value.index:
                            delta_worklist.append((para, callee_function, new_call_context))
                            self.state.update_external_value_match((value, call_context), set({(para, new_call_context)}))
                    
            if value.label == ValueLabel.PARA:
                # Consider side-effect. 
                # Example: the parameter *p is used in the function: p->f = null; 
                # We need to consider the side-effect of p.
                caller_function = self.ts_analyzer.get_all_caller_functions(function)
                for caller_function in caller_function:
                    new_call_context = copy.deepcopy(call_context)
                    is_CFL_reachable_para = new_call_context.add_and_check_context(function.function_id, ContextLabel.RIGHT_PAR)
                    is_CFL_reachable_arg = new_call_context.check_context(caller_function.function_id, ContextLabel.RIGHT_PAR)
                    
                    if not is_CFL_reachable_para or not is_CFL_reachable_arg:
                        continue

                    call_site_nodes = self.ts_analyzer.get_callsites_by_callee_name(caller_function, function.function_name)
                    for call_site_node in call_site_nodes:
                        args = self.ts_analyzer.get_arguments_at_callsite(caller_function, call_site_node)
                        for arg in args:
                            if arg.index == value.index:
                                delta_worklist.append((arg, caller_function, new_call_context))
                                self.state.update_external_value_match((value, call_context), set({(arg, new_call_context)}))
                    
            if value.label == ValueLabel.RET:
                caller_functions = self.ts_analyzer.get_all_caller_functions(function)
                print("The number of caller functions: ", len(caller_functions))
                for caller_function in caller_functions:
                    new_call_context = copy.deepcopy(call_context)
                    is_CFL_reachable_return = new_call_context.add_and_check_context(function.function_id, ContextLabel.RIGHT_PAR)
                    is_CFL_reachable_output = new_call_context.check_context(caller_function.function_id, ContextLabel.RIGHT_PAR)

                    if not is_CFL_reachable_return or not is_CFL_reachable_output:
                        continue

                    call_site_nodes = self.ts_analyzer.get_callsites_by_callee_name(caller_function, function.function_name)
                    for call_site_node in call_site_nodes:
                        output_value = self.ts_analyzer.get_output_value_at_callsite(caller_function, call_site_node)
                        delta_worklist.append((output_value, caller_function, new_call_context))
                        self.state.update_external_value_match((value, call_context), set({(output_value, new_call_context)}))
 
            if value.label == ValueLabel.SINK:
                # No need to continue the exploration
                pass
        return delta_worklist

    def __collect_potential_buggy_paths(self, 
                                        current_value_with_context: Tuple[Value, CallContext],
                                        path_with_unknown_status: List[Value] = []) -> None:
        (current_value, call_context) = current_value_with_context
        if current_value_with_context not in self.state.reachable_values_per_path:
            if not self.is_reachable:
                self.state.update_potential_buggy_paths(path_with_unknown_status)
            return
        
        reachable_values_paths: List[Set[Tuple[Value, CallContext]]] = self.state.reachable_values_per_path[current_value_with_context]
        for i in range(len(reachable_values_paths)):
            for (value, ctx) in reachable_values_paths[i]:
                if value.label == ValueLabel.SINK:
                    # source must not reach sink, e.g., null pointer dereference
                    if self.is_reachable:
                        self.state.update_potential_buggy_paths(path_with_unknown_status + [value])
                elif value.label in {ValueLabel.PARA, ValueLabel.RET, ValueLabel.ARG, ValueLabel.OUT}:
                    if (value, ctx) in self.state.external_value_match:
                        for (value_next, ctx_next) in self.state.external_value_match[(value, ctx)]:
                            self.__collect_potential_buggy_paths((value_next, ctx_next), path_with_unknown_status + [value, value_next])
        return
    
    # TOBE deprecated
    def start_scan_sequential(self) -> None:
        print("Start data-flow bug scanning...")

        for src_value in self.src_values:
            worklist = []
            src_function = self.ts_analyzer.get_function_from_localvalue(src_value)
            if src_function is None:
                continue
            initial_context = CallContext(False)
        
            worklist.append((src_value, src_function, initial_context))
            while len(worklist) > 0:
                (start_value, start_function, call_context) = worklist.pop(0)
                if len(call_context.context) > self.call_depth:
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
                for path_index in range(len(output.reachable_values)):
                    reachable_values_in_single_path = set([])
                    for value in output.reachable_values[path_index]:
                        reachable_values_in_single_path.add((value, call_context))
                    self.state.update_reachable_values_per_path((start_value, call_context), reachable_values_in_single_path)

                    delta_worklist = self.__update_worklist(input, output, call_context, path_index)
                    print("delta_worklist: ", len(delta_worklist))
                    print("worklist: ", len(worklist))
                    worklist.extend(delta_worklist)
                    print("new worklist: ", len(worklist))

            # Output tht reachable values per path
            self.state.print_reachable_values_per_path()
            self.state.print_external_value_match()

            self.__collect_potential_buggy_paths((src_value, CallContext(False)))
            self.state.print_potential_buggy_paths()

            for buggy_path in self.state.potential_buggy_paths.values():
                input = PathValidatorInput(buggy_path, {value: self.ts_analyzer.get_function_from_localvalue(value) for value in buggy_path})
                output: PathValidatorOutput = self.path_validator.invoke(input)
                if output.is_reachable:
                    relevant_functions = {}
                    for value in buggy_path:
                        function = self.ts_analyzer.get_function_from_localvalue(value)
                        if function is not None:
                            relevant_functions[function.function_id] = function

                    bug_report = BugReport(self.bug_type, src_value, relevant_functions, output.poc_str)
                    self.state.update_bug_reports(src_value, bug_report)
            
            # Dump bug reports

            self.bug_reports: dict[Value, List[BugReport]] = {}

            bug_report_dict = {
                str(value): [bug.to_dict() for bug in bug_list]
                for value, bug_list in self.state.bug_reports.items()
            }
            
            with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
                json.dump(bug_report_dict, bug_info_file, indent=4)

            total_bug_number = sum(len(bug_list) for bug_list in self.state.bug_reports.values())
            print(f"{total_bug_number} bug(s) was/were detected in total.")
            print("The bug report(s) has/have been dumped to: ", self.result_dir_path + "/detect_info.json")
        return
    
    def start_scan(self) -> None:
        print("Start data-flow bug scanning in parallel...")

        # Process each source value in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self.__process_src_value, src_value)
                for src_value in self.src_values
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print("Error processing source value:", e)

        # Final summary
        total_bug_number = sum(len(bug_list) for bug_list in self.state.bug_reports.values())
        print(f"{total_bug_number} bug(s) was/were detected in total.")
        print(f"The bug report(s) has/have been dumped to {self.result_dir_path}/detect_info.json")
        return

    def __process_src_value(self, src_value: Value) -> None:
        worklist = []
        src_function = self.ts_analyzer.get_function_from_localvalue(src_value)
        if src_function is None:
            return
        initial_context = CallContext(False)

        worklist.append((src_value, src_function, initial_context))
        while len(worklist) > 0:
            (start_value, start_function, call_context) = worklist.pop(0)
            if len(call_context.context) > self.call_depth:
                continue

            # Construct the input for intra-procedural data-flow analysis
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

            # Invoke the intra-procedural data-flow analysis
            output = self.intra_dfa.invoke(input)
            for path_index in range(len(output.reachable_values)):
                reachable_values_in_single_path = set([])
                for value in output.reachable_values[path_index]:
                    reachable_values_in_single_path.add((value, call_context))
                self.state.update_reachable_values_per_path((start_value, call_context), reachable_values_in_single_path)

                delta_worklist = self.__update_worklist(input, output, call_context, path_index)
                worklist.extend(delta_worklist)

        # Collect potential buggy paths
        self.__collect_potential_buggy_paths((src_value, CallContext(False)))

        # Validate buggy paths and generate bug reports
        for buggy_path in self.state.potential_buggy_paths.values():
            input = PathValidatorInput(buggy_path, {value: self.ts_analyzer.get_function_from_localvalue(value) for value in buggy_path})
            output: PathValidatorOutput = self.path_validator.invoke(input)
            if output.is_reachable:
                relevant_functions = {}
                for value in buggy_path:
                    function = self.ts_analyzer.get_function_from_localvalue(value)
                    if function is not None:
                        relevant_functions[function.function_id] = function

                bug_report = BugReport(self.bug_type, src_value, relevant_functions, output.poc_str)
                self.state.update_bug_reports(src_value, bug_report)

        # Dump bug reports for the current seed
        bug_report_dict = {
            str(value): [bug.to_dict() for bug in bug_list]
            for value, bug_list in self.state.bug_reports.items()
        }
        result_path = os.path.join(self.result_dir_path, "detect_info.json")
        with self.file_lock:  # Ensure thread-safe file writing
            bug_report_dict = {
                str(value): [bug.to_dict() for bug in bug_list]
                for value, bug_list in self.state.bug_reports.items()
            }
            
            with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
                json.dump(bug_report_dict, bug_info_file, indent=4)
        return


    def get_agent_result(self) -> DFBState:
        return self.state
