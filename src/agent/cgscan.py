import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm

from agent.agent import *
from agent.metascan import *

from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *

from llmtool.LLM_utils import *
from llmtool.cgscan.caller_callee_analyzer import *
from memory.semantic.cgscan_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *

from ui.logger import *

BASE_PATH = Path(__file__).resolve().parents[2]


class CGScanAgent(Agent):
    def __init__(
        self,
        project_path: str,
        language: str,
        metascan_agent: MetaScanAgent,
        model_name: str,
        temperature: float,
        max_neural_workers: int = 1,
        agent_id: int = 0,
        include_test_files: bool = False,
    ) -> None:
        self.project_path = project_path
        self.project_name = project_path.split("/")[-1]
        self.language = language if language not in {"C", "Cpp"} else "Cpp"

        self.metascan_agent = metascan_agent
        self.ts_analyzer = metascan_agent.ts_analyzer

        self.model_name = model_name
        self.temperature = temperature

        self.max_neural_workers = max_neural_workers
        self.MAX_QUERY_NUM = 5
        self.include_test_files = include_test_files

        self.lock = threading.Lock()

        with self.lock:
            self.log_dir_path = f"{BASE_PATH}/log/cgscan/{self.model_name}/{self.language}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}-{agent_id}"
            self.res_dir_path = f"{BASE_PATH}/result/cgscan/{self.model_name}/{self.language}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}-{agent_id}"
            if not os.path.exists(self.log_dir_path):
                os.makedirs(self.log_dir_path)
            self.logger = Logger(self.log_dir_path + "/" + "cgscan.log")

            if not os.path.exists(self.res_dir_path):
                os.makedirs(self.res_dir_path)

        self.call_edge_analyzer = CallerCalleeAnalyzer(
            self.model_name,
            self.temperature,
            self.language,
            self.MAX_QUERY_NUM,
            self.logger,
        )

        self.state = CallGraphScanState()
        return

    def query_callee_ids(
        self, caller_id: int, call_site_id: int, is_llm_refined: bool = False
    ) -> List[int]:
        """
        Args:
            caller_id (int): The id of the caller function
            call_site_id (int): The id of the call site in the caller function,
            is_llm_refined (bool, optional): whether the LLMs are enabled. Defaults to False.

        Returns:
            List[int]: The ids of the callee functions
        """
        self.logger.print_console("Start callee querying...")

        if (
            caller_id not in self.ts_analyzer.function_env
            or caller_id not in self.metascan_agent.state.function_meta_data_dict
            or call_site_id
            not in self.metascan_agent.state.function_meta_data_dict[caller_id][
                "call_sites"
            ]
        ):
            return []

        caller_function = self.ts_analyzer.function_env[caller_id]
        call_site_info = self.metascan_agent.state.function_meta_data_dict[caller_id][
            "call_sites"
        ][call_site_id]
        call_site_start_line = call_site_info["call_site_start_line"]
        callee_candidates = []
        for [callee_id, _] in call_site_info["callee_id_name_pairs"]:
            callee_function = self.ts_analyzer.function_env[callee_id]
            callee_candidates.append(callee_function)

        if not is_llm_refined:
            return [
                callee_candidate.function_id for callee_candidate in callee_candidates
            ]
        else:
            return self._process_call_site(
                caller_function, call_site_start_line, callee_candidates
            )

    def query_caller_ids_with_call_site_node_ids(
        self, callee_id: int, is_llm_refined: bool = False
    ) -> Dict[int, List[int]]:
        """
        Args:
            callee_id (int): The id of the callee function
            is_llm_refined (bool, optional): whether the LLMs are enabled. Defaults to False.

        Returns:
            Dict[int, List[int]]: the ids of the caller functions to the call site node ids
        """
        self.logger.print_console("Start caller querying...")

        if (
            callee_id not in self.ts_analyzer.function_env
            or callee_id not in self.metascan_agent.state.function_meta_data_dict
        ):
            return {}

        callee_function = self.ts_analyzer.function_env[callee_id]
        caller_functions = self.ts_analyzer.get_all_caller_functions(callee_function)
        caller_ids_to_call_site_node_ids = {}

        for caller_function in caller_functions:
            call_site_nodes = self.ts_analyzer.get_callsites_by_callee_name(
                caller_function, callee_function.function_name
            )
            for call_site_node in call_site_nodes:
                for call_site_node_id in caller_function.function_call_site_nodes:
                    if (
                        caller_function.function_call_site_nodes[call_site_node_id]
                        == call_site_node
                    ):
                        if (
                            caller_function.function_id
                            not in caller_ids_to_call_site_node_ids
                        ):
                            caller_ids_to_call_site_node_ids[
                                caller_function.function_id
                            ] = [call_site_node_id]
                        else:
                            caller_ids_to_call_site_node_ids[
                                caller_function.function_id
                            ].append(call_site_node_id)

        if not is_llm_refined:
            return caller_ids_to_call_site_node_ids
        else:
            return self._process_caller_ids_with_call_site_node_ids(
                caller_ids_to_call_site_node_ids
            )

    def start_scan(self) -> None:
        self.logger.print_console("Start call graph scanning...")

        # First count total number of call sites to process
        total_tasks = sum(
            1
            for function_id in self.metascan_agent.state.function_meta_data_dict
            for call_site_info in self.metascan_agent.state.function_meta_data_dict[
                function_id
            ]["call_sites"]
            if len(call_site_info["callee_id_name_pairs"]) == 2
        )

        cnt = 5
        total_tasks = cnt

        i = 0
        is_terminate = False

        # Process call sites with progress bar
        with tqdm(total=total_tasks, desc="Analyzing call sites") as pbar:
            # collect the callers and call sites with non-unique callees
            for function_id in self.metascan_agent.state.function_meta_data_dict:
                for call_site_info in self.metascan_agent.state.function_meta_data_dict[
                    function_id
                ]["call_sites"]:
                    # Skip if there are 2 or fewer callee candidates
                    if len(call_site_info["callee_id_name_pairs"]) != 2:
                        continue

                    if i >= cnt:
                        is_terminate = True
                        break
                    i += 1

                    call_site_id = call_site_info["call_site_id"]
                    call_site_start_line = call_site_info["call_site_start_line"]
                    caller_function = self.ts_analyzer.function_env[function_id]

                    # Collect callee candidates
                    callee_candidates = []
                    for [callee_id, _] in call_site_info["callee_id_name_pairs"]:
                        callee_function = self.ts_analyzer.function_env[callee_id]
                        callee_candidates.append(callee_function)

                    try:
                        # Process the call site using the shared method
                        callee_ids = self._process_call_site(
                            caller_function, call_site_start_line, callee_candidates
                        )
                        for callee_id in callee_ids:
                            self.state.update_caller_callee_edges(
                                function_id, call_site_id, callee_id
                            )
                        pbar.update(1)
                    except Exception as e:
                        self.logger.print_log(f"Error processing call site: {str(e)}")
                    break
                if is_terminate:
                    break

        with open(self.res_dir_path + "/callgraph_scan_result.json", "w") as f:
            json.dump(
                self.state.refined_caller_callee_edges, f, indent=4, sort_keys=True
            )

        self.logger.print_console(
            f"The result of cg agent has been dumped to {self.res_dir_path}/callgraph_scan_result.json"
        )

        self.logger.print_console("The log files are as follows:")
        for log_file in self.get_log_files():
            self.logger.print_console(log_file)
        return

    def _process_call_site(
        self,
        caller_function: Function,
        call_site_start_line: int,
        callee_candidates: List[Function],
    ) -> List[int]:
        try:
            # Create input for call edge analyzer
            call_edge_analyzer_input = CallerCalleeAnalyzerInput(
                caller_function,
                call_site_start_line - caller_function.start_line_number + 1,
                callee_candidates,
            )

            # Get analysis result
            call_edge_analyzer_output = self.call_edge_analyzer.invoke(
                call_edge_analyzer_input, CallerCalleeAnalyzerOutput
            )

        except Exception as e:
            self.logger.print_log(f"Error in _process_call_site: {str(e)}")
            raise
        return call_edge_analyzer_output.callee_ids

    def get_agent_state(self) -> CallGraphScanState:
        return self.state

    def get_log_files(self) -> List[str]:
        log_files = []
        log_files.append(self.log_dir_path + "/" + "cgscan.log")
        return log_files
