import json
import os
import threading
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed

from agent.agent import *

from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *

from llmtool.LLM_utils import *
from llmtool.slicescan.intra_slicer import *

from memory.semantic.slicescan_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *

from pathlib import Path
BASE_PATH = Path(__file__).resolve().parents[2]


class SliceScanAgent(Agent):
    def __init__(self,
                 seed_values: List[Value],
                 is_backward: bool,
                 project_path: str,
                 language: str,
                 ts_analyzer: TSAnalyzer,
                 model_name: str,
                 temperature: float,
                 call_depth: int = 1,
                 max_workers: int = 1,
                 ) -> None:
        self.seed_values = seed_values
        self.is_backward = is_backward

        self.project_path = project_path
        self.project_name = project_path.split("/")[-1]

        self.language = language if language not in {"C", "Cpp"} else "Cpp"
        self.ts_analyzer = ts_analyzer

        self.model_name = model_name
        self.temperature = temperature

        self.call_depth = call_depth
        self.max_workers = max_workers
        self.MAX_QUERY_NUM = 5

        self.log_dir_path = f"{BASE_PATH}/log/slicescan-{self.model_name}/{self.language}-{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.log_dir_path):
            os.makedirs(self.log_dir_path)
        self.logger = Logger(self.log_dir_path + "/" + "slicescan.log")

        self.result_dir_path = f"{BASE_PATH}/result/slicescan-{self.model_name}/{self.language}-{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.result_dir_path):
            os.makedirs(self.result_dir_path)
        
        self.seed_function = self.ts_analyzer.get_function_from_localvalue(self.seed_values[0])

        # LLM tool used by SliceScanAgent
        self.intra_slicer = IntraSlicer(self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM, self.logger)

        self.state = SliceScanState(self.seed_function, self.seed_values, self.call_depth, self.is_backward)
        self.worklist_lock = threading.Lock()
        return


    def __update_worklist(self, 
                        input: IntraSlicerInput, 
                        output: IntraSlicerOutput, 
                        slice_context: CallContext
                        ) -> List[Tuple[CallContext, int, Value]]:
        """
        Update the worklist based on the output of the intra-slicer
        :param input: the input of the intra-slicer
        :param output: the output of the intra-slicer
        :param slice_context: the slice context, i.e., the parentheses context calling call stack
        """
        delta_worklist = []  # The list of (slice_context, function_id, a value)
        function_id = input.function.function_id
        function = self.ts_analyzer.function_env[function_id]

        if not self.is_backward:
            # forward slicing
            for external_variable in output.ext_values:
                ext_val_type = external_variable["type"]
            
                if ext_val_type == "Return Value":
                    caller_functions = self.ts_analyzer.get_all_caller_functions(function)
                    for caller_function in caller_functions:
                        # Forward slicing: Return back to caller function from the current function. 
                        new_slice_context = copy.deepcopy(slice_context)
                        top_unmatched_context_label = new_slice_context.get_top_unmatched_context_label()

                        call_site_nodes = self.ts_analyzer.get_callsites_by_callee_name(caller_function, function.function_name)
                        for call_site_node in call_site_nodes:
                            caller_function_file_name = self.ts_analyzer.functionToFile[caller_function.function_id]
                            file_content = self.ts_analyzer.code_in_files[caller_function_file_name]
                            call_site_lower_line_number = file_content[:call_site_node.start_byte].count("\n") + 1

                            if top_unmatched_context_label is not None:
                                if top_unmatched_context_label.parenthesis == Parenthesis.LEFT_PAR:
                                    if call_site_lower_line_number != top_unmatched_context_label.line_number \
                                        or caller_function_file_name != top_unmatched_context_label.file_name \
                                        or top_unmatched_context_label.function_id != function.function_id:
                                        continue
                            
                            append_context_label = ContextLabel(
                                caller_function_file_name, 
                                call_site_lower_line_number, 
                                function.function_id, 
                                Parenthesis.RIGHT_PAR)
                            new_slice_context.add_and_check_context(append_context_label)
                            output_value = self.ts_analyzer.get_output_value_at_callsite(caller_function, call_site_node)
                            delta_worklist.append((new_slice_context, caller_function.function_id, output_value))

                elif ext_val_type == "Argument":
                    callee_name = external_variable["callee_name"]
                    index = external_variable["index"]
                    callee_functions = [
                        function
                        for function in self.ts_analyzer.get_all_callee_functions(function)
                        if function.function_name == callee_name
                    ]
                    for callee_function in callee_functions:
                        call_sites = self.ts_analyzer.get_callsites_by_callee_name(function, callee_function.function_name)
                        for call_site_node in call_sites:
                            file_content = self.ts_analyzer.code_in_files[function.file_path]
                            call_site_lower_line_number = file_content[:call_site_node.start_byte].count("\n") + 1
                            
                            new_slice_context = copy.deepcopy(slice_context)
                            context_label = ContextLabel(
                                self.ts_analyzer.functionToFile[function.function_id], 
                                call_site_lower_line_number, 
                                callee_function.function_id, 
                                Parenthesis.LEFT_PAR)
                            is_CFL_reachable = new_slice_context.add_and_check_context(context_label)
                            if not is_CFL_reachable:
                                continue
                            
                            for para in callee_function.paras:
                                if para.index == index:
                                    delta_worklist.append((new_slice_context, callee_function.function_id, para))

                elif ext_val_type == "Parameter":
                    # Consider side-effect. 
                    # Example: the parameter *p is used in the function: p->f = null; 
                    # We need to consider the side-effect of p.
                    caller_functions = self.ts_analyzer.get_all_caller_functions(function)
                    index = external_variable["index"]

                    for caller_function in caller_functions:
                        new_slice_context = copy.deepcopy(slice_context)
                        top_unmatched_context_label = new_slice_context.get_top_unmatched_context_label()

                        call_site_nodes = self.ts_analyzer.get_callsites_by_callee_name(caller_function, function.function_name)
                        for call_site_node in call_site_nodes:
                            caller_function_file_name = self.ts_analyzer.functionToFile[caller_function.function_id]
                            file_content = self.ts_analyzer.code_in_files[caller_function_file_name]
                            call_site_lower_line_number = file_content[:call_site_node.start_byte].count("\n") + 1

                            if top_unmatched_context_label is not None:
                                if top_unmatched_context_label.parenthesis == Parenthesis.LEFT_PAR:
                                    if call_site_lower_line_number != top_unmatched_context_label.line_number \
                                        or caller_function_file_name != top_unmatched_context_label.file_name \
                                        or top_unmatched_context_label.function_id != function.function_id:
                                        continue

                            append_context_label = ContextLabel(
                                caller_function_file_name, 
                                call_site_lower_line_number, 
                                function.function_id, 
                                Parenthesis.RIGHT_PAR)
                            new_slice_context.add_and_check_context(append_context_label)

                            args = self.ts_analyzer.get_arguments_at_callsite(caller_function, call_site_node)
                            for arg in args:
                                if arg.index == index:
                                    delta_worklist.append((new_slice_context, caller_function.function_id, arg))

                elif ext_val_type == "Global Variable":
                    # TODO: add global variable support
                    pass

        else:
            # backward slicing
            for external_variable in output.ext_values:
                ext_val_type = external_variable["type"]
                if ext_val_type == "Output Value":
                    callee_name = external_variable["callee_name"]
                    callee_functions = [
                        function
                        for function in self.ts_analyzer.get_all_callee_functions(function)
                        if function.function_name == callee_name
                    ]
                    for callee_function in callee_functions:
                        call_sites = self.ts_analyzer.get_callsites_by_callee_name(function, callee_function.function_name)
                        for call_site_node in call_sites:
                            file_content = self.ts_analyzer.code_in_files[function.file_path]
                            call_site_lower_line_number = file_content[:call_site_node.start_byte].count("\n") + 1
                            
                            new_slice_context = copy.deepcopy(slice_context)
                            context_label = ContextLabel(
                                self.ts_analyzer.functionToFile[function.function_id], 
                                call_site_lower_line_number, 
                                callee_function.function_id, 
                                Parenthesis.RIGHT_PAR)
                            new_slice_context.add_and_check_context(context_label)
                            ret_values = self.ts_analyzer.get_return_values_in_single_function(callee_function)
                            for ret_value in ret_values:
                                delta_worklist.append((new_slice_context, callee_function.function_id, ret_value))

                elif ext_val_type == "Parameter":
                    index = external_variable["index"]
                    caller_functions = self.ts_analyzer.get_all_caller_functions(function)
                    for caller_function in caller_functions:
                        # Backward slicing: Trace back to the caller function from the current function
                        new_slice_context = copy.deepcopy(slice_context)
                        top_unmatched_context_label = new_slice_context.get_top_unmatched_context_label()

                        call_site_nodes = self.ts_analyzer.get_callsites_by_callee_name(caller_function, function.function_name)
                        for call_site_node in call_site_nodes:
                            caller_function_file_name = self.ts_analyzer.functionToFile[caller_function.function_id]
                            file_content = self.ts_analyzer.code_in_files[caller_function_file_name]
                            call_site_lower_line_number = file_content[:call_site_node.start_byte].count("\n") + 1
                        
                            if top_unmatched_context_label is not None:
                                if top_unmatched_context_label.parenthesis == Parenthesis.RIGHT_PAR:
                                    if call_site_lower_line_number != top_unmatched_context_label.line_number \
                                        or caller_function_file_name != top_unmatched_context_label.file_name \
                                        or top_unmatched_context_label.function_id != function.function_id:
                                        continue
                            
                            append_context_label = ContextLabel(
                                caller_function_file_name, 
                                call_site_lower_line_number, 
                                function.function_id, 
                                Parenthesis.LEFT_PAR)
                            new_slice_context.add_and_check_context(append_context_label)

                            args = self.ts_analyzer.get_arguments_at_callsite(caller_function, call_site_node)
                            for arg in args:
                                if arg.index == index:
                                    delta_worklist.append((new_slice_context, caller_function.function_id, arg))

                elif ext_val_type == "Argument":
                    # Consider side-effect. 
                    # Example: the argument *p used at a call site foo(p) is further utilized, i.e., x = p->f; 
                    # We need to consider the side-effect of the callee foo.
                    callee_name = external_variable["callee_name"]
                    callee_functions = [
                        function
                        for function in self.ts_analyzer.get_all_callee_functions(function)
                        if function.function_name == callee_name
                    ]
                    index = external_variable["index"]
                    for callee_function in callee_functions:
                        # Backward slicing: Trace back to the callee function from the current function
                        call_sites = self.ts_analyzer.get_callsites_by_callee_name(function, callee_function.function_name)
                        for call_site_node in call_sites:
                            file_content = self.ts_analyzer.code_in_files[function.file_path]
                            call_site_lower_line_number = file_content[:call_site_node.start_byte].count("\n") + 1
                            
                            new_slice_context = copy.deepcopy(slice_context)
                            context_label = ContextLabel(
                                self.ts_analyzer.functionToFile[function.function_id], 
                                call_site_lower_line_number, 
                                callee_function.function_id, 
                                Parenthesis.RIGHT_PAR)
                            is_CFL_reachable = new_slice_context.add_and_check_context(context_label)
                            if not is_CFL_reachable:
                                continue
                            
                            for para in callee_function.paras:
                                if para.index == index:
                                    delta_worklist.append((new_slice_context, callee_function.function_id, para))
        return delta_worklist


    # TOBE deprecated
    def start_scan_sequential(self) -> None:
        self.logger.print_console("Start slice scanning...")
        worklist: List[Tuple[CallContext, int, Set[Value]]] = [] # The list of (slice_contxt, function_id, set of seed_value)

        # Initially, the call stack is empty.
        initial_context = CallContext(self.is_backward)
        worklist.append((initial_context, self.seed_function.function_id, self.seed_values))

        while True:
            if len(worklist) == 0:
                break

            (slice_context, function_id, seed_set) = worklist.pop(0)
            if len(slice_context.context) > self.state.call_depth:
                continue

            input: IntraSlicerInput = IntraSlicerInput(self.ts_analyzer.function_env[function_id], seed_set, self.is_backward)
            output: IntraSlicerOutput = self.intra_slicer.invoke(input)

            if output is None:
                continue

            self.state.update_intra_slices_in_state(slice_context, self.ts_analyzer.function_env[function_id], seed_set, output.slice)

            # Add more functions to the worklist according to the external variables in the intra-slicing output
            delta_worklist = self.__update_worklist(input, output, slice_context)
            for (delta_slice_context, delta_function_id, delta_seed_value) in delta_worklist:
                is_mergeable = False
                for (worklist_slice_context, worklist_function_id, worklist_seed_set) in worklist:
                    if delta_slice_context != worklist_slice_context or delta_function_id != worklist_function_id:
                        continue
                    worklist_seed_value = list(worklist_seed_set)[0]
                    if (delta_seed_value.label == ValueLabel.RET and worklist_seed_value.label == ValueLabel.RET) \
                        or (delta_seed_value.line_number == worklist_seed_value.line_number):
                        worklist_seed_set.update({delta_seed_value})
                        is_mergeable = True
                        break
                if not is_mergeable:
                    worklist.append((delta_slice_context, delta_function_id, {delta_seed_value}))
        return

    def __process_item(self, item: Tuple[CallContext, int, Set[Value]]) -> List[Tuple[CallContext, int, Set[Value]]]:
        """
        Process one worklist item and return the delta worklist.
        """
        slice_context, function_id, seed_set = item

        # If call depth exceeds allowed limit, skip processing.
        if len(slice_context.context) >= self.state.call_depth:
            return []

        input_data = IntraSlicerInput(self.ts_analyzer.function_env[function_id], seed_set, self.is_backward)
        output = self.intra_slicer.invoke(input_data)

        if output is None:
            return []

        self.state.update_intra_slices_in_state(slice_context, self.ts_analyzer.function_env[function_id], seed_set, output.slice)

        delta_worklist = self.__update_worklist(input_data, output, slice_context)
        return delta_worklist

    def start_scan(self) -> None:
        self.logger.print_console("Start slice scanning in parallel...")
        # worklist: list of tuples (CallContext, function_id, set of seed values)
        worklist: List[Tuple[CallContext, int, Set[Value]]] = []
        initial_context = CallContext(self.is_backward)
        worklist.append((initial_context, self.seed_function.function_id, self.seed_values))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while worklist:
                futures = [executor.submit(self.__process_item, item) for item in worklist]
                # Clear worklist for the next iteration
                worklist = []

                for future in as_completed(futures):
                    try:
                        delta_items = future.result()
                    except Exception as e:
                        continue

                    # Protect the merging of new delta items into the worklist.
                    with self.worklist_lock:
                        for (delta_slice_context, delta_function_id, delta_seed_value) in delta_items:
                            is_mergeable = False
                            for i, (wl_slice_context, wl_function_id, wl_seed_set) in enumerate(worklist):
                                if delta_slice_context == wl_slice_context and delta_function_id == wl_function_id:
                                    wl_seed_value = list(wl_seed_set)[0]
                                    if (delta_seed_value.label == ValueLabel.RET and wl_seed_value.label == ValueLabel.RET) \
                                        or (delta_seed_value.line_number == wl_seed_value.line_number):
                                        wl_seed_set.update({delta_seed_value})
                                        is_mergeable = True
                                        break
                            if not is_mergeable:
                                worklist.append((delta_slice_context, delta_function_id, {delta_seed_value}))
        return

    def get_agent_state(self) -> SliceScanState:
        return self.state
    
    def get_log_files(self) -> List[str]:
        log_files = []
        log_files.append(self.log_dir_path + "/" + "slicescan.log")
        return log_files