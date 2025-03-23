import json
import os
import threading
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *
from llmtool.LLM_utils import *
from memory.semantic.slicescan_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *
from llmtool.intra_slicer import *
from pathlib import Path
BASE_PATH = Path(__file__).resolve().parents[2]


class SliceScanAgent:
    def __init__(self,
                 seed_values: List[Value],
                 is_backward: bool,
                 project_path: str,
                 language: str,
                 ts_analyzer: TSAnalyzer,
                 model_name: str,
                 temperature: float,
                 call_depth: int = 1,
                 max_workers: int = 1
                 ) -> None:
        self.seed_values = seed_values
        self.is_backward = is_backward

        self.project_path = project_path
        self.language = language if language not in {"C", "Cpp"} else "Cpp"
        self.ts_analyzer = ts_analyzer

        self.model_name = model_name
        self.temperature = temperature

        self.call_depth = call_depth
        self.max_workers = max_workers
        self.MAX_QUERY_NUM = 5

        self.log_dir_path = f"{BASE_PATH}/log/slicescan-{self.model_name}/{self.project_path}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.log_dir_path):
            os.makedirs(self.log_dir_path)

        self.result_dir_path = f"{BASE_PATH}/result/slicescan-{self.model_name}/{self.project_path}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.result_dir_path):
            os.makedirs(self.result_dir_path)

        # # TODO: For demo testing
        # if len(self.seed_values) == 0:
        #     for function_id in self.ts_analyzer.function_env:
        #         if self.ts_analyzer.function_env[function_id].function_name == "Exec":
        #             function = self.ts_analyzer.function_env[function_id]
        #             rets = self.ts_analyzer.get_return_values_in_single_function(function)
        #             self.seed_values = list(rets)
        
        self.seed_function = self.ts_analyzer.get_function_from_localvalue(self.seed_values[0])

        # LLM tool used by SliceScanAgent
        self.intra_slicer = IntraSlicer(self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM)

        self.state = SliceScanState(self.seed_function, self.seed_values, self.call_depth, self.is_backward)
        return


    def __update_worklist(self, 
                        input: IntraSlicerInput, 
                        output: IntraSlicerOutput, 
                        slice_context: CallContext
                        ) -> List[Tuple[int, Value]]:
        """
        Update the worklist based on the output of the intra-slicer
        :param input: the input of the intra-slicer
        :param output: the output of the intra-slicer
        :param slice_context: the slice context, i.e., the parentheses context calling call stack
        """
        delta_worklist = []  # The list of (slice_context, function_id, a singleton of value)
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
                        is_CFL_reachable = new_slice_context.add_context(function_id, ContextLabel.RIGHT_PAR)

                        # violate CFL reachability and then skip
                        if not is_CFL_reachable:
                            continue
                        print("call edge: ", caller_function.function_name, " --> ", function.function_name)

                        call_site_nodes = self.ts_analyzer.get_callsites_by_callee_name(caller_function, function.function_name)
                        for call_site_node in call_site_nodes:
                            output_value = self.ts_analyzer.get_output_value_at_callsite(caller_function, call_site_node)
                            delta_worklist.append((new_slice_context, caller_function.function_id, set([output_value])))

                elif ext_val_type == "Argument":
                    callee_name = external_variable["callee_name"]
                    index = external_variable["index"]
                    callee_functions = [
                        function
                        for function in self.ts_analyzer.get_all_callee_functions(function)
                        if function.function_name == callee_name
                    ]
                    for callee_function in callee_functions:
                        new_slice_context = copy.deepcopy(slice_context)
    
                        # Forward slicing: Step into the callee function from the current function
                        new_slice_context = copy.deepcopy(slice_context)
                        is_CFL_reachable = new_slice_context.add_context(callee_function.function_id, ContextLabel.LEFT_PAR)

                        # violate CFL reachability and then skip
                        if not is_CFL_reachable:
                            continue
                        print("call edge: ", function.function_name, " --> ", callee_function.function_name)

                        parameter_list = self.ts_analyzer.get_parameters_in_single_function(callee_function)
                        for parameter in parameter_list:
                            if parameter.index == index:
                                delta_worklist.append((new_slice_context, callee_function.function_id, set([parameter])))

                elif ext_val_type == "Parameter":
                    # Consider side-effect. 
                    # Example: the parameter *p is used in the function: p->f = null; 
                    # We need to consider the side-effect of p.
                    caller_functions = self.ts_analyzer.get_all_caller_functions(function)
                    index = external_variable["index"]

                    for caller_function in caller_functions:
                        new_slice_context = copy.deepcopy(slice_context)

                        # Forward slicing: Return back to caller function from the current function. 
                        new_slice_context = copy.deepcopy(slice_context)
                        is_CFL_reachable = new_slice_context.add_context(function_id, ContextLabel.RIGHT_PAR)

                        # violate CFL reachability and then skip
                        if not is_CFL_reachable:
                            continue
                        print("call edge: ", caller_function.function_name, " --> ", function.function_name)

                        call_site_nodes = self.ts_analyzer.get_callsites_by_callee_name(caller_function, function.function_name)
                        for call_site_node in call_site_nodes:
                            args = self.ts_analyzer.get_arguments_at_callsite(caller_function, call_site_node)
                            # TODO: For better precision (field-sensitivity), we can consider to transform the argument name to a specific access path
                            for arg in args:
                                if arg.index == index:
                                    delta_worklist.append((new_slice_context, caller_function.function_id, set([arg])))

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
                        # Backward slicing: Trace back to the callee function from the current function
                        new_slice_context = copy.deepcopy(slice_context)
                        is_CFL_reachable = new_slice_context.add_context(callee_function.function_id, ContextLabel.RIGHT_PAR)

                        # violate CFL reachability and then skip
                        if not is_CFL_reachable:
                            continue
                        print("call edge: ", function.function_name, " --> ", callee_function.function_name)

                        ret_values = self.ts_analyzer.get_return_values_in_single_function(callee_function)
                        for ret_value in ret_values:
                            delta_worklist.append((new_slice_context, callee_function.function_id, set([ret_value])))

                elif ext_val_type == "Parameter":
                    index = external_variable["index"]
                    caller_functions = self.ts_analyzer.get_all_caller_functions(function)
                    for caller_function in caller_functions:
                        # Backward slicing: Trace back to the caller function from the current function
                        new_slice_context = copy.deepcopy(slice_context)
                        is_CFL_reachable = new_slice_context.add_context(function_id, ContextLabel.LEFT_PAR)

                        # violate CFL reachability and then skip
                        if not is_CFL_reachable:
                            continue
                        print("call edge: ", caller_function.function_name, " --> ", function.function_name)

                        call_sites = self.ts_analyzer.get_callsites_by_callee_name(caller_function, function.function_name)
                        for call_site in call_sites:
                            args = self.ts_analyzer.get_arguments_at_callsite(caller_function, call_site)
                            for arg in args:
                                if arg.index == index:
                                    caller_function_file_content = self.ts_analyzer.fileContentDic[caller_function.file_path]
                                    callsite_str = caller_function_file_content[call_site.start_byte:call_site.end_byte]
                                    callsite_line_number = caller_function_file_content[:call_site.start_byte].count("\n") + 1 - caller_function.start_line_number
                                    delta_worklist.append((new_slice_context, caller_function.function_id, set([arg])))

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
                        new_slice_context = copy.deepcopy(slice_context)
                        is_CFL_reachable = new_slice_context.add_context(callee_function.function_id, ContextLabel.RIGHT_PAR)

                        # violate CFL reachability and then skip
                        if not is_CFL_reachable:
                            continue
                        print("call edge: ", function.function_name, " --> ", callee_function.function_name)

                        parameters = self.ts_analyzer.get_parameters_in_single_function(callee_function)
                        for parameter in parameters:
                            if parameter.index == index:
                                # TODO: For better precision (field-sensitivity), we can consider to transform the parameter name to a specific access path
                                delta_worklist.append((new_slice_context, callee_function.function_id, set([parameter])))

                elif ext_val_type == "Global Variable":
                    # TODO: add other global support, especially the memory operations (read and write) upon global variables and concurrency issues
                    global_variable_name = external_variable["variable_name"]
                    if global_variable_name in self.ts_analyzer.glb_var_map:
                        macro = f"Global Variable: \n ```\n{global_variable_name} = {self.ts_analyzer.glb_var_map[global_variable_name]} \n```\n"
                        self.update_global_slices_in_state(macro)
        return delta_worklist


    def start_scan(self):
        print("Start slice scanning...")
        worklist: List[Tuple[CallContext, int, Set[Value]]] = [] # The list of (slice_contxt, function_id, set of seed_value)

        # Initially, the call stack is empty.
        initial_context = CallContext(self.is_backward)
        worklist.append((initial_context, self.seed_function.function_id, self.seed_values))

        while True:
            if len(worklist) == 0:
                break

            print("==================================================")
            print("Peek and analyze one item in worklist...")
            print("# Remaining items in worklist: ", len(worklist))
            print("==================================================")

            (slice_context, function_id, seed_set) = worklist.pop(0)
            if len(slice_context.context) > self.state.call_depth:
                print("The call depth is reached. Skip slicing it.")
                continue

            input: IntraSlicerInput = IntraSlicerInput(self.ts_analyzer.function_env[function_id], seed_set, self.is_backward)
            output: IntraSlicerOutput = self.intra_slicer.invoke(input)
            self.state.update_intra_slices_in_state(slice_context, self.ts_analyzer.function_env[function_id], seed_set, output.slice)

            # Add more functions to the worklist according to the external variables in the intra-slicing output
            delta_worklist = self.__update_worklist(input, output, slice_context)
            print("length of delta_worklist: ", len(delta_worklist))
            print("length of worklist: ", len(worklist))

            for (delta_slice_context, delta_function_id, delta_seed_set) in delta_worklist:
                delta_seed_value = list(delta_seed_set)[0]
                is_mergeable = False
                for (worklist_slice_context, worklist_function_id, worklist_seed_set) in worklist:
                    if delta_slice_context != worklist_slice_context or delta_function_id != worklist_function_id:
                        continue
                    worklist_seed_value = list(worklist_seed_set)[0]
                    if (delta_seed_value.label == ValueLabel.RET and worklist_seed_value.label == ValueLabel.RET) \
                        or (delta_seed_value.line_number == worklist_seed_value.line_number):
                        worklist_seed_set.update(delta_seed_set)
                        is_mergeable = True
                        break
                if not is_mergeable:
                    worklist.append((delta_slice_context, delta_function_id, delta_seed_set))

        # def sequential():
        #     # Start to analyze each seed
        #     for (seed_value, is_forward) in seeds:
        #         seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
        #         if seed_function == None:
        #             continue
                
        #         # Construct an analysis state and retrieve callers/callees during forward/backward slicing
        #         seed_state = BugScanState(seed_value, seed_function)
        #         if is_forward:
        #             flag = self.forward_slicing_analyzer.analyze(seed_state, 0)
        #         else:
        #             flag = self.backward_slicing_analyzer.analyze(seed_state, 0)

        #         # flag: whether the LLM format is valid or not.
        #         # Slices are generated if flag is True.
        #         if not flag:
        #             continue

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


    def get_agent_state(self) -> SliceScanState:
        return self.state