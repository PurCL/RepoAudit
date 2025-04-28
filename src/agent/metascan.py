import json
import os

from agent.agent import *
from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *
from llmtool.LLM_utils import *
from memory.semantic.metascan_state import *
from pathlib import Path


class MetaScanAgent(Agent):
    """
    This agent is designed to extract meta information from the source code.
    Used for testing llmtools :)
    """

    def __init__(self, project_path, language, ts_analyzer) -> None:
        self.project_path = project_path
        self.project_name = project_path.split("/")[-1]
        self.language = language
        self.ts_analyzer = ts_analyzer
        self.state = MetaScanState()
        return

    def start_scan(self) -> None:
        """
        Start the detection process.
        """
        log_dir_path = str(
            Path(__file__).resolve().parent.parent.parent
            / f"result/metascan/{self.language}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        )
        if not os.path.exists(log_dir_path):
            os.makedirs(log_dir_path)
        self.logger = Logger(self.log_dir_path + "/" + "metascan.log")

        for function_id in self.ts_analyzer.function_env:
            function_meta_data = {}
            function = self.ts_analyzer.function_env[function_id]
            function_meta_data["function_id"] = function.function_id
            function_meta_data["function_name"] = function.function_name
            function_meta_data["function_start_line"] = function.start_line_number
            function_meta_data["function_end_line"] = function.end_line_number

            function_meta_data["parameters"] = [str(para) for para in function.paras]

            function_meta_data["retvals"] = [str(retval) for retval in function.retvals]

            function_meta_data["call_sites"] = []
            for call_site in function.function_call_site_nodes:
                call_site_info = {}
                file_content = self.ts_analyzer.fileContentDic[function.file_path]
                call_site_info["callee_id"] = (
                    self.ts_analyzer.get_callee_function_ids_at_callsite(
                        function, call_site
                    )
                )
                call_site_info["args"] = [
                    str(arg)
                    for arg in self.ts_analyzer.get_arguments_at_callsite(
                        function, call_site
                    )
                ]
                call_site_info["call_site_start_line"] = (
                    file_content[: call_site.start_byte].count("\n") + 1
                )
                function_meta_data["call_sites"].append(call_site_info)

            # function call
            function_meta_data["function_callee_ids"] = []
            if function_id in self.ts_analyzer.function_caller_callee_map:
                for callee_id in self.ts_analyzer.function_caller_callee_map[
                    function_id
                ]:
                    function_meta_data["function_callee_ids"].append(callee_id)

            # api call
            function_meta_data["api_callee_strs"] = []
            if function_id in self.ts_analyzer.function_caller_api_callee_map:
                for callee_id in self.ts_analyzer.function_caller_api_callee_map[
                    function_id
                ]:
                    function_meta_data["api_callee_strs"].append(
                        str(self.ts_analyzer.api_env[callee_id])
                    )

            function_meta_data["caller_ids"] = []
            if function_id in self.ts_analyzer.function_callee_caller_map:
                for caller_id in self.ts_analyzer.function_callee_caller_map[
                    function_id
                ]:
                    function_meta_data["caller_ids"].append(caller_id)

            # control flow
            function_meta_data["if_statements"] = []
            for (
                if_statement_start_line,
                if_statement_end_line,
            ) in self.ts_analyzer.function_env[function_id].if_statements:
                (
                    condition_start_line,
                    condition_end_line,
                    condition_str,
                    (true_branch_start_line, true_branch_end_line),
                    (else_branch_start_line, else_branch_end_line),
                ) = self.ts_analyzer.function_env[function_id].if_statements[
                    (if_statement_start_line, if_statement_end_line)
                ]
                if_statement = {}
                if_statement["condition_str"] = condition_str
                if_statement["condition_start_line"] = condition_start_line
                if_statement["condition_end_line"] = condition_end_line
                if_statement["true_branch_start_line"] = true_branch_start_line
                if_statement["true_branch_end_line"] = true_branch_end_line
                if_statement["else_branch_start_line"] = else_branch_start_line
                if_statement["else_branch_end_line"] = else_branch_end_line
                function_meta_data["if_statements"].append(if_statement)

            function_meta_data["loop_statements"] = []
            for (
                loop_statement_start_line,
                loop_statement_end_line,
            ) in self.ts_analyzer.function_env[function_id].loop_statements:
                (
                    header_start_line,
                    header_end_line,
                    header_str,
                    loop_body_start_line,
                    loop_body_end_line,
                ) = self.ts_analyzer.function_env[function_id].loop_statements[
                    (loop_statement_start_line, loop_statement_end_line)
                ]
                loop_statement = {}
                loop_statement["loop_statement_start_line"] = loop_statement_start_line
                loop_statement["loop_statement_end_line"] = loop_statement_end_line
                loop_statement["header_str"] = header_str
                loop_statement["header_start_line"] = header_start_line
                loop_statement["header_end_line"] = header_end_line
                loop_statement["loop_body_start_line"] = loop_body_start_line
                loop_statement["loop_body_end_line"] = loop_body_end_line
                function_meta_data["loop_statements"].append(loop_statement)

            self.state.update_function_meta_data(function_id, function_meta_data)

        with open(log_dir_path + "/meta_scan_result.json", "w") as f:
            json.dump(self.state.function_meta_data_dict, f, indent=4, sort_keys=True)

        f2f_call_edge_num = 0
        f2a_call_edge_num = 0
        for callee, callers in self.ts_analyzer.function_callee_caller_map.items():
            f2f_call_edge_num += len(callers)
        for callee, callers in self.ts_analyzer.function_caller_api_callee_map.items():
            f2a_call_edge_num += len(callers)

        self.logger.print_console(
            "Function Number: ", len(self.state.function_meta_data_dict)
        )
        self.logger.print_console("API Number: ", len(self.ts_analyzer.api_env))
        self.logger.print_console(
            "Function-Function Call Edge Number: ", f2f_call_edge_num
        )
        self.logger.print_console("Function-API Call Edge Number: ", f2a_call_edge_num)
        return

    def get_agent_state(self):
        return self.state
