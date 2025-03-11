import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.C_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from llmtool.LLM_utils import *
from memory.semantic.state import BugScanState
from memory.syntactic.function import *
from memory.syntactic.value import *
from llmtool.backward_slicer import BackwardSlicer
from llmtool.forward_slicer import ForwardSlicer
from pathlib import Path
BASE_PATH = Path(__file__).resolve().parents[2]


class BugScanAgent:
    def __init__(self,
                 seed_spec_file,
                 project_name,
                 language,
                 all_files,
                 inference_model_name,
                 temperature,
                 bug_type,
                 boundary,
                 max_workers=1
                 ) -> None:
        self.seed_spec_file = seed_spec_file
        self.project_name = project_name
        self.language = language
        self.all_files = all_files
        self.model_name = inference_model_name
        self.temperature = temperature
        self.bug_type = bug_type
        self.boundary = boundary
        self.max_workers = max_workers

        self.detection_prompt_file = f"{BASE_PATH}/src/prompt/detection/{language}/{language}_{self.bug_type}_prompt.json"
        self.inline_prompt_file = f"{BASE_PATH}/src/prompt/llmtool/{language}/{language}_inline_prompt.json"
        self.MAX_QUERY_NUM = 5
        self.detection_role = self.fetch_detection_system_role()
        
        self.detection_result = []
        if self.language == "C" or self.language == "C++":
            self.ts_analyzer = C_TSAnalyzer(self.all_files, self.language)
        elif self.language == "Go":
            self.ts_analyzer = Go_TSAnalyzer(self.all_files, self.language)
        elif self.language == "Java":
            self.ts_analyzer = Java_TSAnalyzer(self.all_files, self.language)
        else:
            print("Unsupported language")
            exit(1)
        
        self.backward_slicing_analyzer = BackwardSlicer(
            self.model_name, 
            self.temperature, 
            self.language, 
            self.ts_analyzer,
            self.boundary
        )
        self.forward_slicing_analyzer = ForwardSlicer(
            self.model_name, 
            self.temperature, 
            self.language, 
            self.ts_analyzer,
            self.boundary
        )

        self.run_info = {}
        self.bug_info = {}

        self.result_dir_path = f"{BASE_PATH}/result/bugscan-{self.model_name}/{self.bug_type}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.result_dir_path):
            os.makedirs(self.result_dir_path)
    

    def start_scan(self):
        log_dir_path = str(
            Path(__file__).resolve().parent.parent.parent / (f"log/{self.bug_type}/{self.project_name}")
        )
        if not os.path.exists(log_dir_path):
            os.makedirs(log_dir_path)

        print("Start bug scanning...")

        seeds = []
        with open (self.seed_spec_file, "r") as f:
            seed_spec = json.load(f)
        for seed_str in seed_spec:
            if seed_str.strip("\n").endswith(" 1"):
                is_forward = True
                seed_value = Value.from_str_to_value(seed_str.strip("\n").strip(" 1"))
            elif seed_str.strip("\n").endswith(" 0"):
                is_forward = False
                seed_value = Value.from_str_to_value(seed_str.strip("\n").strip(" 0"))
            seeds.append((seed_value, is_forward))
            
        def sequential():
            # Start to analyze each seed
            for (seed_value, is_forward) in seeds:
                seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
                if seed_function == None:
                    continue
                
                # Construct an analysis state and retrieve callers/callees during forward/backward slicing
                seed_state = BugScanState(seed_value, seed_function)
                if is_forward:
                    flag = self.forward_slicing_analyzer.analyze(seed_state, 0)
                else:
                    flag = self.backward_slicing_analyzer.analyze(seed_state, 0)

                # flag: whether the LLM format is valid or not.
                # Slices are generated if flag is True.
                if not flag:
                    continue

                # Detect the bugs upon slices using LLM (inlining enabled)
                key = seed_state.get_key()
                if is_forward:
                    self.run_info[key] = self.forward_slicing_analyzer.result_list
                else:
                    self.run_info[key] = self.backward_slicing_analyzer.result_list
                answer, poc = self.detect_with_llm(seed_state)
                
                # For DEBUG
                print("====================================")
                print("Is Bug: ", answer)
                print("PoC: ", poc)
                print("===============================================")

                # Dump bug reports
                with open(self.result_dir_path + "/slicing_info.json", 'w') as run_info_file:
                    json.dump(self.run_info, run_info_file, indent=4)

                with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
                    json.dump(self.bug_info, bug_info_file, indent=4)
        

        def parallel(n):
            lock = threading.Lock()
            
            def worker(seed):
                (seed_value, is_forward) = seed
                seed_function = self.ts_analyzer.get_function_from_localvalue(seed_value)
                if seed_function is None:
                    return

                # Construct an analysis state and retrieve callers/callees during forward/backward slicing
                seed_state = BugScanState(seed_value, seed_function)
                if is_forward:
                    flag = self.forward_slicing_analyzer.analyze(seed_state, 0)
                else:
                    flag = self.backward_slicing_analyzer.analyze(seed_state, 0)

                # flag: whether the LLM format is valid or not.
                # Slices are generated if flag is True.
                if not flag:
                    return

                # Detect the bugs upon slices using LLM (inlining enabled)
                key = seed_state.get_key()
                if is_forward:
                    self.run_info[key] = self.forward_slicing_analyzer.result_list
                else:
                    self.run_info[key] = self.backward_slicing_analyzer.result_list
                answer, poc = self.detect_with_llm(seed_state)

                # For DEBUG
                print("====================================")
                print("Is Bug: ", answer)
                print("PoC: ", poc)
                print("===============================================")

                # Use lock to protect file writes
                with lock:
                    with open(self.result_dir_path + "/slicing_info.json", 'w') as run_info_file:
                        json.dump(self.run_info, run_info_file, indent=4)
                    with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
                        json.dump(self.bug_info, bug_info_file, indent=4)

            # Process at most n src concurrently
            with ThreadPoolExecutor(max_workers=n) as executor:
                futures = [executor.submit(worker, seed) for seed in seeds]
                for future in as_completed(futures):
                    # Could log exceptions here if needed
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Error processing src: {e}")
        
        if self.max_workers == 1:
            sequential()
        else:
            parallel(self.max_workers)
        

    def detect_with_llm(self, state:BugScanState) -> Tuple[str, str]:
        """
        Detect the bug with LLM
        """
        ## For DEBUG
        print("Detecting with LLM...")
        solve_model = LLM(self.model_name, self.temperature, self.detection_role)
        key = state.get_key()
        self.bug_info[key] = []
        root_states = state.find_root()
        for root_state in root_states:
            inline_code = self.inline_with_LLM(root_state)
            print("inline code:\n", inline_code)

            message = self.fetch_detection_prompt()
            message = message.replace("<FUNCTION>", inline_code)
            message = message.replace("<SEED_NAME>", state.var.name)

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
                
                self.bug_info[key].append({"Call Tree": root_state.get_call_tree(), "Inlined Function": inline_code, "Output": output, "Is Bug": answer, "PoC": poc})
                break
            if answer == "Yes":
                break
        return answer, poc
    

    def inline_with_LLM(self, state: BugScanState) -> str:
        """
        Inline the slices with LLM
        """
        slices = set(state.get_slice_tree())
        with open(self.inline_prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        role = dump_config_dict["system_role"].replace("<LANGUAGE>", self.language)
        solve_model = LLM(self.model_name, self.temperature, role)
        message = dump_config_dict["task"]
        message += "\n" + "".join(dump_config_dict["meta_prompts"])
        message = message.replace("<ANSWER>", "\n".join(dump_config_dict["answer_format"]))
        message = message.replace("<FUNCTION>", "\n".join(slices))
        
        ## append call tree
        call_tree_prompt = dump_config_dict["call_tree"]
        call_tree_prompt = call_tree_prompt.replace("<FUNCTION_NAME>", state.function.function_name)
        call_tree_prompt = call_tree_prompt.replace("<FUNCTION_CALL_TREE>", state.get_call_tree())
        message += "\n" + call_tree_prompt

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
            

    def fetch_detection_prompt(self) -> str:
        """
        Fetch the detection prompt, leaving the placeholders <FUNCTION> and <SEED_NAME> to be filled
        """
        with open(self.detection_prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        message = dump_config_dict["task"]
        message += "\n" + "\n".join(dump_config_dict["analysis_rules"])
        # message += "\n" + "\n".join(dump_config_dict["analysis_examples"])
        message += "\n" + "".join(dump_config_dict["meta_prompts"])
        message = message.replace("<ANSWER>", "\n".join(dump_config_dict["answer_format"]))
        message = message.replace("<QUESTION>", dump_config_dict["question_template"])
        return message
    

    def fetch_detection_system_role(self) -> str:
        with open(self.detection_prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        role = dump_config_dict["system_role"].replace("<LANGUAGE>", self.language)
        return role
