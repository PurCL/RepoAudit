import json
import os
from parser.response_parser import *
from parser.program_parser import *
from prompt.apiscan_prompt import *
from utility.llm import *
from pathlib import Path

class APIScanPipeline:
    def __init__(self,
                 project_name,
                 language,
                 all_files,
                 inference_model_name,
                 inference_key_str,
                 temperature):
        self.project_name = project_name
        self.language = language
        self.all_files = all_files
        self.inference_model_name = inference_model_name
        self.inference_key_str = inference_key_str
        self.temperature = temperature

        self.scanning_result = []
        self.buggy_traces = []
        self.ts_analyzer = TSAnalyzer(self.all_files, self.language)
        self.model = LLM(self.inference_model_name, self.inference_key_str, self.temperature)

    def start_scan(self):
        """
        Start the scanning process.
        """
        log_dir_path = str(
            Path(__file__).resolve().parent.parent.parent / ("log/apiscan/" + self.project_name)
        )
        if not os.path.exists(log_dir_path):
            os.makedirs(log_dir_path)

        probe_scope = {}
        sensitive_functions = set(prompt_dict.keys())
        all_scanning_scopes = {}

        for sensitive_function in set(sensitive_functions):
            if sensitive_function != "mhi_alloc_controller":
                continue
            print(sensitive_function)
            scanning_scopes = self.extract_scan_scopes(sensitive_function)
            all_scanning_scopes[sensitive_function] = scanning_scopes
            probe_scope[sensitive_function] = []
            for function_id in scanning_scopes:
                probe_scope[sensitive_function].append(self.ts_analyzer.environment[function_id].function_name)
        
        with open(log_dir_path + "/probe_scope.json", 'w') as f:
            json.dump(probe_scope, f, indent=4, sort_keys=True)
        print(probe_scope)

        report = {}
        for sensitive_function in all_scanning_scopes:
            report[sensitive_function] = []
            cnt = 1
            for function_id in all_scanning_scopes[sensitive_function]:
                print(cnt, "/", len(all_scanning_scopes[sensitive_function]))
                cnt += 1
                print("Start analyzing the function: ", self.ts_analyzer.environment[function_id].function_name)

                function_code = self.ts_analyzer.environment[function_id].function_code
                prompt_template = prompt_dict[sensitive_function]
                response, input_token_cost, output_token_cost = self.model.infer(prompt_template.replace("{function_code}", function_code), False)
                is_buggy = parse_bug_report(response)
                report[sensitive_function].append({
                    "function_name": self.ts_analyzer.environment[function_id].function_name,
                    "response": response,
                    "is_buggy": is_buggy
                })

        with open(log_dir_path + "/api_scan_result.json", 'w') as f:
            json.dump(report, f, indent=4, sort_keys=True)
        return
    
    def extract_scan_scopes(self, api_name: str):
        """
        Extract scanning scopes for a given API name.
        """

        print("Start extracting scanning scopes")
        target_function_ids = {}
        cnt = 0
        for function_id in self.ts_analyzer.ts_parser.functionRawDataDic:
            cnt += 1
            print(cnt, "/", len(self.ts_analyzer.ts_parser.functionRawDataDic))

            function_root_node = self.ts_analyzer.environment[function_id].parse_tree_root_node
            all_call_sites = self.ts_analyzer.find_nodes_by_type(function_root_node, "call_expression")
            is_target = False
            for call_site in all_call_sites:
                file_id = self.ts_analyzer.ts_parser.functionToFile[function_id]
                file_content = self.ts_analyzer.ts_parser.fileContentDic[file_id]
                if file_content[call_site.start_byte:call_site.end_byte].find(api_name + "(") != -1:
                    is_target = True
                    break
            if is_target:
                target_function_ids[function_id] = self.ts_analyzer.environment[function_id].function_name
        print("Finish extracting scanning scopes")
        return target_function_ids
