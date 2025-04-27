import json
import os
import re
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

from llmtool.LLM_utils import *
from llmtool.debugscan.debug_request_formulator import *
from llmtool.debugscan.debug_slice_analyzer import *

from memory.semantic.debugscan_state import *
from memory.syntactic.function import *
from memory.syntactic.value import *

from ui.logger import *

BASE_PATH = Path(__file__).resolve().parents[2]


class DebugScanAgent(Agent):
    def __init__(self,
                project_path,
                language,
                ts_analyzer,
                model_name,
                temperature,
                call_depth,
                max_neural_workers = 1,
                agent_id: int = 0,
                ) -> None:
        self.project_path = project_path
        self.project_name = project_path.split("/")[-1]
        self.language = language if language not in {"C", "Cpp"} else "Cpp"
        self.ts_analyzer = ts_analyzer

        self.model_name = model_name
        self.temperature = temperature
        
        self.call_depth = call_depth
        self.max_neural_workers = max_neural_workers
        self.MAX_QUERY_NUM = 5

        self.lock = threading.Lock()

        with self.lock:
            self.log_dir_path = f"{BASE_PATH}/log/debugscan/{self.model_name}/{self.language}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}-{agent_id}"
            self.res_dir_path = f"{BASE_PATH}/result/debugscan/{self.model_name}/{self.bug_type}/{self.language}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}-{agent_id}"
            if not os.path.exists(self.log_dir_path):
                os.makedirs(self.log_dir_path)
            self.logger = Logger(self.log_dir_path + "/" + "debugscan.log")
            
            if not os.path.exists(self.res_dir_path):
                os.makedirs(self.res_dir_path)

        # LLM tools used by DebugScanAgent
        self.debug_request_formulator = DebugRequestFormulator(self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM, self.logger)
        self.debug_slice_analyzer = DebugSliceAnalyzer(self.model_name, self.temperature, self.language, self.MAX_QUERY_NUM, self.logger)
        self.slice_scan_agent: SliceScanAgent = None

        self.error_message, self.error_function_name, self.error_file_path, self.error_line_number, self.debug_request = self.__receive_audit_request()
        self.seed: Value = None
        self.state = DebugScanState(self.error_message)
        return
    
    def __receive_audit_request(self) -> Tuple[str, str, str, int, str]:
        while True:
            # self.logger.print_console("Please enter the runtime error message:")
            # sys.stdout.write(">>> ")
            # sys.stdout.flush()
            # error_message = sys.stdin.readline().strip()

            error_message = """
Exception in thread "main" java.lang.NullPointerException: Cannot invoke "String.length()" because "<parameter1>" is null
        at debug.TestCase1.processConfiguration(TestCase1.java:49)
        at debug.TestCase1.main(TestCase1.java:16)
"""
            
            self.logger.print_console("Please enter your debugging request:")
            sys.stdout.write(">>> ")
            sys.stdout.flush()
            user_request_str = sys.stdin.readline().strip()

            pattern = re.compile(r'at\s+([\w\.]+)\.([\w<$>]+)\(([^:]+):(\d+)\)')
            m = pattern.search(error_message)
            if m:
                full_class, method, file, line = m.groups()
                pkg = full_class.rsplit('.', 1)[0]            
                file_path = pkg.replace('.', '/') + '/' + file 
                if line.isdigit():
                    line_number = int(line)
                else:
                    self.logger.print_console("Invalid line number. Please try again.")
                    continue
            else:
                self.logger.print_console("Invalid error message format. Please try again.")
                continue
            break
        return error_message, method, file_path, line_number, user_request_str
    
    def start_scan(self) -> None:
        self.logger.print_console("Start debug scanning...")

        # Step I: Extract the debug seed
        crash_function = None
        for function_id, function in self.ts_analyzer.function_env.items():
            if function.function_name == self.error_function_name:
                if function.start_line_number <= self.error_line_number <= function.end_line_number:
                    crash_function = function
                    break
        if crash_function is None:
            self.logger.print_console(f"Cannot find the function {self.error_function_name} in the project. Please check the error message.")
            return
        
        lined_function_code = crash_function.attach_absolute_line_number()
        debug_request_input = DebugRequestFormulatorInput(self.error_message, lined_function_code, crash_function.file_path, self.debug_request)
        debug_request_output: DebugRequestFormulatorOutput = self.debug_request_formulator.invoke(debug_request_input)
        self.state.update_debug_seed(debug_request_output.debug_seed)

        # Step II: Slice from the debug seed
        self.slice_scan_agent = SliceScanAgent(
            [debug_request_output.debug_seed],
            True,
            self.project_path,
            self.language,
            self.ts_analyzer,
            self.model_name,
            self.temperature,
            self.call_depth,
            self.max_neural_workers
        )
        self.slice_scan_agent.start_scan()

        # Step III: Analyze the debug slice and get the debug result
        debug_slice = self.slice_scan_agent.get_agent_state().get_result()
        self.debug_slice_analyzer_input = DebugSliceAnalyzerInput(self.error_message, debug_request_output.debug_seed, debug_slice, self.debug_request)
        self.debug_slice_analyzer_output: DebugSliceAnalyzerOutput = self.debug_slice_analyzer.invoke(self.debug_slice_analyzer_input)

        debug_report = DebugReport(self.error_message, 
                                   debug_request_output.debug_seed, 
                                   debug_request_output.debug_seed, 
                                   self.debug_slice_analyzer_output.explanation_str)
        self.state.update_debug_report(debug_report)

        debug_report_dict = {
            "error_message": self.error_message,
            "debug_seed": str(debug_request_output.debug_seed),
            "debug_slice": str(debug_slice),
            "explanation": str(self.debug_slice_analyzer_output.explanation_str),
        }

        with open(self.res_dir_path + "/detect_info.json", 'w') as debug_report:
            json.dump(debug_report_dict, debug_report, indent=4)

        self.logger.print_console(f"The bug report(s) has/have been dumped to {self.res_dir_path}/detect_info.json")
        self.logger.print_console("The log files are as follows:")
        for log_file in self.get_log_files():
            self.logger.print_console(log_file)
        return
        
    def get_agent_state(self) -> DebugScanState:
        return self.state
    
    def get_log_files(self) -> List[str]:
        log_files = []
        log_files.append(self.log_dir_path + "/" + "debugscan.log")
        log_files.append(self.slice_scan_agent.log_dir_path + "/" + "slicescan.log")
        return log_files
