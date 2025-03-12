import json
import os
from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *
from llmtool.LLM_utils import *
from llmtool.LLM_utils import *
from pathlib import Path

class MetaScanAgent:
    """
    This agent is designed to extract meta information from the source code.
    Used for testing llmtools :)
    """
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
        if self.language == "C" or self.language == "Cpp":
            self.ts_analyzer = Cpp_TSAnalyzer(self.all_files, self.language)
        elif self.language == "Go":
            self.ts_analyzer = Go_TSAnalyzer(self.all_files, self.language)
        elif self.language == "Java":
            self.ts_analyzer = Java_TSAnalyzer(self.all_files, self.language)
        elif self.language == "Python":
            self.ts_analyzer = Python_TSAnalyzer(self.all_files, self.language)
        else:
            print("Unsupported language")
            exit(1)
        self.model = LLM(self.inference_model_name, self.temperature)

    def start_scan(self):
        """
        Start the detection process.
        """
        log_dir_path = str(
            Path(__file__).resolve().parent.parent.parent / ("result/metascan/" + self.project_name)
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
            function_meta_data["retstmts"] = list(function.retsmts)

            function_meta_data["call_sites"] = []
            for call_site in function.call_site_nodes:
                call_site_info = {}
                file_content = self.ts_analyzer.ts_parser.fileContentDic[function.file_name]
                call_site_info["callee_id"] = self.ts_analyzer.get_callee_at_callsite(call_site, file_content)
                call_site_info["args"] = list(self.ts_analyzer.get_arguments_at_callsite(call_site, file_content))
                call_site_info["call_site_start_line"] = file_content[:call_site.start_byte].count("\n") + 1
                function_meta_data["call_sites"].append(call_site_info)

            # function call
            function_meta_data["callee_ids"] = []
            if function_id in self.ts_analyzer.caller_callee_map:
                for callee_id in self.ts_analyzer.caller_callee_map[function_id]:
                    function_meta_data["callee_ids"].append(callee_id)
            
            function_meta_data["caller_ids"] = []
            if function_id in self.ts_analyzer.callee_caller_map:
                for caller_id in self.ts_analyzer.callee_caller_map[function_id]:
                    function_meta_data["caller_ids"].append(caller_id)
    
            # control flow
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
    