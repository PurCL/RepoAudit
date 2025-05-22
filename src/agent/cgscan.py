import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tqdm import tqdm

from agent.agent import *

from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *

from llmtool.LLM_utils import *

from memory.semantic.cgscan_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *

from ui.logger import *

BASE_PATH = Path(__file__).resolve().parents[2]


class CGScanAgent(Agent):
    def __init__(
        self,
        project_path,
        language,
        ts_analyzer,
        model_name,
        temperature,
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

        self.max_neural_workers = max_neural_workers
        self.MAX_QUERY_NUM = 5
        self.include_test_files = include_test_files

        self.lock = threading.Lock()

        with self.lock:
            self.log_dir_path = f"{BASE_PATH}/log/cgscan/{self.model_name}/{self.language}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}-{agent_id}"
            self.res_dir_path = f"{BASE_PATH}/result/cgscan/{self.model_name}/{self.bug_type}/{self.language}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}-{agent_id}"
            if not os.path.exists(self.log_dir_path):
                os.makedirs(self.log_dir_path)
            self.logger = Logger(self.log_dir_path + "/" + "cgscan.log")

            if not os.path.exists(self.res_dir_path):
                os.makedirs(self.res_dir_path)

        # TODO

        self.state = CallGraphScanState()
        return

    # TOBE deprecated
    def start_scan_sequential(self) -> None:
        self.logger.print_console("Start call graph scanning...")

        # TODO

        # Final summary
        # total_bug_number = len(self.state.bug_reports.values())
        # self.logger.print_console(
        #     f"{total_bug_number} bug(s) was/were detected in total."
        # )
        # self.logger.print_console(
        #     f"The bug report(s) has/have been dumped to {self.res_dir_path}/detect_info.json"
        # )
        self.logger.print_console("The log files are as follows:")
        for log_file in self.get_log_files():
            self.logger.print_console(log_file)
        return

    def start_scan(self) -> None:
        self.logger.print_console("Start data-flow bug scanning in parallel...")
        self.logger.print_console(f"Max number of workers: {self.max_neural_workers}")

        # TODO

        # Final summary
        # total_bug_number = len(self.state.bug_reports.values())
        # self.logger.print_console(
        #     f"{total_bug_number} bug(s) was/were detected in total."
        # )
        # self.logger.print_console(
        #     f"The bug report(s) has/have been dumped to {self.res_dir_path}/detect_info.json"
        # )
        self.logger.print_console("The log files are as follows:")
        for log_file in self.get_log_files():
            self.logger.print_console(log_file)
        return

    def get_agent_state(self) -> CallGraphScanState:
        return self.state

    def get_log_files(self) -> List[str]:
        log_files = []
        log_files.append(self.log_dir_path + "/" + "cgscan.log")
        return log_files
