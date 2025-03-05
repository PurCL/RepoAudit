import json
import os
from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.C_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from llmtool.LLM_utils import *
from llmtool.LLM_utils import *
from pathlib import Path

class MetaScanAgent:
    def __init__(self,
                 project_name,
                 language,
                 all_files,
                 inference_model_name,
                 temperature):
        self.project_name = project_name
        self.language = language
        self.all_files = all_files
        self.inference_model_name = inference_model_name
        self.temperature = temperature

        self.detection_result = []
        self.buggy_traces = []
        self.ts_analyzer = TSAnalyzer(self.all_files, self.language)
        self.model = LLM(self.inference_model_name, self.temperature)

    def start_scan(self):
        """
        Start the detection process.
        """
        log_dir_path = str(
            Path(__file__).resolve().parent.parent.parent / ("log/metascan/" + self.project_name)
        )
        if not os.path.exists(log_dir_path):
            os.makedirs(log_dir_path)

        call_edge_num = 0

        function_meta_data_dict = {}

        for function_id in self.ts_analyzer.environment:
            function_meta_data = {}
            function = self.ts_analyzer.environment[function_id]
            function_meta_data["function_id"] = function.function_id
            function_meta_data["function_name"] = function.function_name
            function_meta_data["function_start_line"] = function.start_line_number
            function_meta_data["function_end_line"] = function.end_line_number

            function_meta_data["parameters"] = list(function.paras)

            function_meta_data["if_statements"] = []
            for (if_statement_start_line, if_statement_end_line) in self.ts_analyzer.environment[function_id].if_statements:
                (
                    condition_start_line,
                    condition_end_line,
                    condition_str,
                    (true_branch_start_line, true_branch_end_line),
                    (else_branch_start_line, else_branch_end_line)
                ) = self.ts_analyzer.environment[function_id].if_statements[(if_statement_start_line, if_statement_end_line)]
                if_statement = {}
                if_statement["condition_str"] = condition_str
                if_statement["condition_start_line"] = condition_start_line
                if_statement["condition_end_line"] = condition_end_line
                if_statement["true_branch_start_line"] = true_branch_start_line
                if_statement["true_branch_end_line"] = true_branch_end_line
                if_statement["else_branch_start_line"] = else_branch_start_line
                if_statement["else_branch_end_line"] = else_branch_end_line
                function_meta_data["if_statements"].append(if_statement)

            function_meta_data_dict[function_id] = function_meta_data

            function_meta_data["loop_statements"] = []
            for (loop_statement_start_line, loop_statement_end_line) in self.ts_analyzer.environment[function_id].loop_statements:
                (
                    
                    header_start_line,
                    header_end_line,
                    header_str,
                    loop_body_start_line,
                    loop_body_end_line
                ) = self.ts_analyzer.environment[function_id].loop_statements[(loop_statement_start_line, loop_statement_end_line)]
                loop_statement = {}
                loop_statement["loop_statement_start_line"] = loop_statement_start_line
                loop_statement["loop_statement_end_line"] = loop_statement_end_line
                loop_statement["header_str"] = header_str
                loop_statement["header_start_line"] = header_start_line
                loop_statement["header_end_line"] = header_end_line
                loop_statement["loop_body_start_line"] = loop_body_start_line
                loop_statement["loop_body_end_line"] = loop_body_end_line
                function_meta_data["loop_statements"].append(loop_statement)

        with open(log_dir_path + "/meta_scan_result.json", 'w') as f:
            json.dump(function_meta_data_dict, f, indent=4, sort_keys=True)
        
        for callee, callers in self.ts_analyzer.callee_caller_map.items():
            call_edge_num += len(callers)

        print("Function Number: ", len(function_meta_data_dict))
        print("Call Edge Number: ", call_edge_num)
        
        return
    