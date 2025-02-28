import json
import os
from parser.response_parser import *
from parser.program_parser import *
from parser.ts_transform import *
from utility.llm import *
from utility.nmr_state import State
from utility.function import *
from utility.localvalue import *
# from LMAgent.nmr_validator import NeumericValidator
from LMAgent.nmr_analyzer import NeumericAnalyzer
from pathlib import Path


class NeumericBugScanPipeline:
    def __init__(self,
                 src_spec_file,
                 sink_spec_file,
                 analyze_prompt_file,
                 validate_prompt_file,
                 project_name,
                 language,
                 all_files,
                 inference_model_name,
                 temperature,
                 is_fscot,
                 bug_type,
                 boundary=2):
        self.src_spec_file = src_spec_file
        self.sink_spec_file = sink_spec_file
        self.analyze_prompt_file = analyze_prompt_file
        self.validate_prompt_file = validate_prompt_file
        self.project_name = project_name
        self.language = language
        self.all_files = all_files
        self.bug_type = bug_type
        self.boundary = boundary
        self.model_name = inference_model_name
        self.temp = temperature
        self.MAX_QUERY_NUM = 5
        
        self.detection_result = []
        self.ts_analyzer = TSAnalyzer(self.all_files, self.language)
        self.function_processor = TSFunctionProcessor(self.ts_analyzer, self.language)
        self.nmr_analyzer = NeumericAnalyzer(
            self.analyze_prompt_file, 
            self.model_name, 
            temperature, 
            self.language, 
            self.ts_analyzer, 
            self.function_processor, 
            is_fscot,
            self.boundary,
            self.bug_type
            )
        self.run_info = {}
        self.solve_info = {}
    
    def start_scan(self):
        log_dir_path = str(
            Path(__file__).resolve().parent.parent.parent / (f"log/{self.bug_type}/{self.project_name}")
        )
        if not os.path.exists(log_dir_path):
            os.makedirs(log_dir_path)

        result_dir_path = str(
            Path(__file__).resolve().parent.parent.parent / (f"result-{self.model_name}/{self.bug_type}/{self.project_name}")
        )
        if not os.path.exists(result_dir_path):
            os.makedirs(result_dir_path)
        print("Start Neumeric scan...")

        src_list = []
        with open (self.src_spec_file, "r") as f:
            src_spec = json.load(f)
        for src in src_spec:
            src_value = LocalValue.from_string(src)
            if src_value:
                src_list.append(src_value)
        
        # For BOF, we need to extract the buffer and index variable
        if self.bug_type == "BOF":
            for i, src in enumerate(src_list):
                name = src.name
                src_list[i].buffer = name.split("[")[0]
                src_list[i].index_var = name.split("[")[-1][:-1]
        
        for src in src_list:
            # Get source function body

            if str(src) != "((buffer[len++], -1, 253), ValueType.SINK, ../benchmark/C/curl/lib/sendf.c)":
                continue

            src_function = self.ts_analyzer.get_function_from_localvalue(src)
            if src_function == None:
                continue
            
            if self.bug_type == "BOF":
                # For BOF, we need to extract and analyze the buffer and index variable
                buffer = LocalValue(src.name.split("[")[0], src.line_number, ValueType.BUF, src.file)
                index_var = LocalValue(src.name.split("[")[-1][:-1], src.line_number, ValueType.VAR, src.file)
                src_state = State(index_var, src_function, "Index")
                result = self.nmr_analyzer.analyze(src_state, 0)
                if not result:
                    continue
                buffer_state = State(buffer, src_function, "Buffer Size")
                result = self.nmr_analyzer.analyze(buffer_state, 0)
                if not result:
                    continue
                src_state.var = src
                src_state.children.append(buffer_state)
            else:
                src_state = State(src, src_function)
                result = self.nmr_analyzer.analyze(src_state, 0)
                if not result:
                    continue

            key = (src.line_number, src_function.function_name, src_function.file_name)
            self.run_info[str(key)] = self.nmr_analyzer.result_list

            src_state.print_all_expressions()
            print("============================")
            expressions_list = src_state.get_all_expressions()
            clauses = []
            for expressions in expressions_list:
                if expressions == []:
                    continue
                # expression_literal = [f"({expression})" for expression in expressions]
                # expression_clause = " || ".join(expression_literal)
                # clauses.append(f"({expression_clause})")
                expression_clause = str(expressions)
                clauses.append(expression_clause)
                print(expression_clause)
            if self.bug_type == "BOF":
                clauses.extend(["[Buffer Size > 0]", "[Index <= Buffer Size]"])
            conjunction = " && ".join(clauses)
            solve_result = self.solve_with_llm(conjunction, key)
            

        with open(result_dir_path + "/run_info.json", 'w') as run_info_file:
            json.dump(self.run_info, run_info_file, indent=4)

        with open(result_dir_path + "/solve_info.json", 'w') as solve_info_file:
            json.dump(self.solve_info, solve_info_file, indent=4)

    
    def solve_with_llm(self, conjunction, key="") -> str:
        """
        Solve the conjunction with LLM
        """
        with open(self.validate_prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        role = dump_config_dict["system_role"]
        solve_model = LLM(self.model_name, self.temp, role)
        answer = "\n".join(dump_config_dict["answer_format"])
        message = dump_config_dict["task"]
        message += "\n" + "".join(dump_config_dict["meta_prompts"])
        message = message.replace("<CONJUNCTION>", conjunction)
        message = message.replace("<ANSWER>", answer)
        output, input_token_cost, output_token_cost = solve_model.infer(message, True)
        result = ""
        if "Yes" in output:
            result = "Yes"
        if "No" in output:
            result = "No"
        self.solve_info[str(key)] = {"Conjunction": conjunction, "Result": result, "Message":message, "Output": output}

        # For DEBUG
        print("====================================")
        print("Result: ", result)
        print("Response: ", output)
        print("===============================================")


        return result
            


        
                

