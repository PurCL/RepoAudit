import json
import os
from parser.program_parser import *
from parser.ts_transform import *
from utility.llm import *
from utility.nmr_state import State
from utility.function import *
from utility.localvalue import *
from LMAgent.bot2up_analyzer import Bot2UpAnalyzer
from pathlib import Path


class NeumericBugScanPipeline:
    def __init__(self,
                 src_spec_file,
                 sink_spec_file,
                 analyze_prompt_file,
                 detection_prompt_file,
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
        self.detection_prompt_file = detection_prompt_file
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
        self.analyzer = Bot2UpAnalyzer(
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
        self.bug_info = {}
    

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
        
        for src in src_list:
            # Get source function body
            
            # # Project curl
            # if str(src) != "((buffer[len++], -1, 253), ValueType.SINK, ../benchmark/C/curl/lib/sendf.c)":
            #     continue

            # # Project php-src
            if str(src) != "((malloc(length + 1), -1, 2670), ValueType.BUF, ../benchmark/C/php-src/Zend/zend_alloc.c)":
                continue

            src_function = self.ts_analyzer.get_function_from_localvalue(src)
            if src_function == None:
                continue
            
            src_state = State(src, src_function)
            result = self.analyzer.analyze(src_state, 0)
            if not result:
                continue

            key = src_state.get_key()
            self.run_info[key] = self.analyzer.result_list

            answer, poc = self.detect_with_llm(src_state)
            
            # For DEBUG
            print("====================================")
            print("Is Bug: ", answer)
            print("PoC: ", poc)
            print("===============================================")

        with open(result_dir_path + "/slicing_info.json", 'w') as run_info_file:
            json.dump(self.run_info, run_info_file, indent=4)

        with open(result_dir_path + "/detect_info.json", 'w') as bug_info_file:
            json.dump(self.bug_info, bug_info_file, indent=4)

    
    def detect_with_llm(self, state:State) -> Tuple[str, str]:
        """
        Detect the bug with LLM
        """
        slice_list = state.get_all_slices()
        inline_code = self.inline_with_LLM(slice_list)
        with open(self.detection_prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        role = dump_config_dict["system_role"].replace("<LANGUAGE>", self.language)
        solve_model = LLM(self.model_name, self.temp, role)
        message = dump_config_dict["task"]
        message += "\n" + "\n".join(dump_config_dict["analysis_rules"])
        # message += "\n" + "\n".join(dump_config_dict["analysis_examples"])
        message += "\n" + "".join(dump_config_dict["meta_prompts"])
        message = message.replace("<ANSWER>", "\n".join(dump_config_dict["answer_format"]))
        message = message.replace("<QUESTION>", dump_config_dict["question_template"])

        message = message.replace("<FUNCTION>", inline_code)
        message = message.replace("<SRC_NAME>", state.var.name)

        current_query_num = 0
        while current_query_num < self.MAX_QUERY_NUM:
            current_query_num += 1
            output, input_token_cost, output_token_cost = solve_model.infer(message, True)
            
            answer_match = re.search(r'Answer:\s*(\w+)', output)
            poc_match = re.search(r'PoC:\s*(.*)', output, re.DOTALL)
            if answer_match:
                answer = answer_match.group(1).strip()
            else:
                print(f"Answer not found in output")
                continue
            poc = poc_match.group(1).strip() if poc_match else ""
            
            key = state.get_key()
            self.bug_info[key] = {"Message":message, "Output": output, "Slices": slice_list, "Inlined Function": inline_code, "Is Bug": answer, "PoC": poc}
            break
        return answer, poc
    

    def inline_with_LLM(self, slices:list[str]):
        """
        Inline the slices with LLM
        """
        inline_prompt_file = "/data4/guo846/RepoAudit-Neumeric/src/prompt/BOF/inline_prompt.json"
        with open(inline_prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        role = dump_config_dict["system_role"].replace("<LANGUAGE>", self.language)
        solve_model = LLM(self.model_name, self.temp, role)
        message = dump_config_dict["task"]
        message += "\n" + "".join(dump_config_dict["meta_prompts"])
        message = message.replace("<ANSWER>", "\n".join(dump_config_dict["answer_format"]))
        message = message.replace("<FUNCTION>", "\n".join(slices))
        
        current_query_num = 0
        while current_query_num < self.MAX_QUERY_NUM:
            current_query_num += 1
            output, input_token_cost, output_token_cost = solve_model.infer(message, True)
            
            pattern = re.compile(r"```(?:\w+)?\s*([\s\S]*?)\s*```")
            match = pattern.search(output)
            if match:
                return match.group(1).strip()
            else:
                print(f"Inline function not found in output")

        return ""
            
