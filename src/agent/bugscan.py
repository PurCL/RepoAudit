import json
import os
from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.C_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from llmtool.LLM_utils import *
from memory.state import State
from memory.function import *
from memory.localvalue import *
from llmtool.backward_slicer import BackwardSlicer
from llmtool.forward_slicer import ForwardSlicer
from pathlib import Path
BASE_PATH = Path(__file__).resolve().parents[2]
BACKWARD_BUG_TYPE = ("BOF")
FORWARD_BUG_TYPE = ("NPD", "UAF", "MLK")


class BugScanAgent:
    def __init__(self,
                 src_spec_file,
                 project_name,
                 language,
                 all_files,
                 inference_model_name,
                 temperature,
                 bug_type,
                 boundary
                 ) -> None:
        self.src_spec_file = src_spec_file
        self.project_name = project_name
        self.language = language
        self.all_files = all_files
        self.model_name = inference_model_name
        self.temp = temperature
        self.bug_type = bug_type
        self.boundary = boundary
        self.detection_prompt_file = f"{BASE_PATH}/src/prompt/detection/{self.bug_type}_prompt.json"
        self.inline_prompt_file = f"{BASE_PATH}/src/prompt/llmtool/inline_prompt.json"
        self.MAX_QUERY_NUM = 5
        self.detection_role = self.fetch_detection_system_role()
        
        self.detection_result = []
        if self.language == "C" or self.language == "C++":
            self.ts_analyzer = C_TSAnalyzer(self.all_files, self.language)
        elif self.language == "Go":
            self.ts_analyzer = Go_TSAnalyzer(self.all_files, self.language)
        else:
            print("Unsupported language")
            exit(1)
        
        if self.bug_type in BACKWARD_BUG_TYPE:
            self.analyzer = BackwardSlicer(
                self.model_name, 
                self.temp, 
                self.language, 
                self.ts_analyzer,
                self.boundary
            )
        elif self.bug_type in FORWARD_BUG_TYPE:
            self.analyzer = ForwardSlicer(
                self.model_name, 
                self.temp, 
                self.language, 
                self.ts_analyzer,
                self.boundary
            )
        else:
            print("Unsupported bug type")
            exit(1)
        self.run_info = {}
        self.bug_info = {}

        self.result_dir_path = f"{BASE_PATH}/result/detect-{self.model_name}/{self.bug_type}/{self.project_name}/{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}"
        if not os.path.exists(self.result_dir_path):
            os.makedirs(self.result_dir_path)
    

    def start_scan(self):
        log_dir_path = str(
            Path(__file__).resolve().parent.parent.parent / (f"log/{self.bug_type}/{self.project_name}")
        )
        if not os.path.exists(log_dir_path):
            os.makedirs(log_dir_path)

        print("Start bug scanning...")

        src_list = []
        with open (self.src_spec_file, "r") as f:
            src_spec = json.load(f)
        for src in src_spec:
            src_value = LocalValue.from_string(src)
            if src_value:
                src_list.append(src_value)
        
        for src in src_list:
            # Get source function body
            
            # ## Project curl
            # if str(src) != "((buffer[len++], -1, 253), ValueType.SINK, ../benchmark/C/curl/lib/sendf.c)":
            #     continue

            # ## Project php-src
            # if str(src) != "((malloc(length + 1), -1, 2670), ValueType.BUF, ../benchmark/C/php-src/Zend/zend_alloc.c)":
            #     continue

            ## Project zstd
            if str(src) != "((newTable->fileNames[newTableIdx], -1, 563), ValueType.BUF, ../benchmark/C/zstd/programs/util.c)":
                continue

            # ## Project cpv-1
            # if str(src) != "((*u, -1, 4091), ValueType.BUF, ../benchmark/C/cpv-1/src/http/ngx_http_request.c)":
            #     continue

            # ## Project cpv-3
            # if str(src) != "((*b->last++, -1, 4092), ValueType.BUF, ../benchmark/C/cpv-3/src/http/ngx_http_request.c)":
            #     continue

            ## Project cpv-3-repair
            # if str(src) != "((*b->last++, -1, 4097), ValueType.BUF, ../benchmark/C/cpv-3-repair/src/http/ngx_http_request.c)":
            #     continue

            # ## Project cpv-8
            # if str(src) != "((    ngx_memcpy(s->login.data, arg[0].data, s->login.len);, -1, 324), ValueType.SRC, ../benchmark/C/cpv-8/src/mail/ngx_mail_pop3_handler.c)":
            #     continue
            
            # ## Project cpv-8-repair
            # if str(src) != "((    ngx_memcpy(s->login.data, arg[0].data, s->login.len);, -1, 324), ValueType.SRC, ../benchmark/C/cpv-8-repair/src/mail/ngx_mail_pop3_handler.c)":
            #     continue

            # ## Project cpv-12
            # if str(src) != "((rev[j], -1, 77), ValueType.BUF, ../benchmark/C/cpv-12/src/os/unix/ngx_linux_sendfile_chain.c)":
            #     continue

            # ## Project cpv-12-repair
            # if str(src) != "((rev[j], -1, 77), ValueType.BUF, ../benchmark/C/cpv-12-repair/src/os/unix/ngx_linux_sendfile_chain.c)":
            #     continue

            # ## memcached
            # if str(src) != "((char *list = strdup(settings.inter);, -1, 4629), ValueType.SRC, ../benchmark/C/memcached/memcached.c)":
            #     continue

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

        with open(self.result_dir_path + "/slicing_info.json", 'w') as run_info_file:
            json.dump(self.run_info, run_info_file, indent=4)

        with open(self.result_dir_path + "/detect_info.json", 'w') as bug_info_file:
            json.dump(self.bug_info, bug_info_file, indent=4)

    
    def detect_with_llm(self, state:State) -> Tuple[str, str]:
        """
        Detect the bug with LLM
        """
        ## For DEBUG
        print("Detecting with LLM...")
        solve_model = LLM(self.model_name, self.temp, self.detection_role)
        key = state.get_key()
        self.bug_info[key] = []
        root_states = state.find_root()
        for root_state in root_states:
            inline_code = self.inline_with_LLM(root_state)

            message = self.fetch_detection_prompt()
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
                
                self.bug_info[key].append({"Call Tree": root_state.get_call_tree(), "Inlined Function": inline_code, "Output": output, "Is Bug": answer, "PoC": poc})
                break
            if answer == "Yes":
                break
        return answer, poc
    

    def inline_with_LLM(self, state: State) -> str:
        """
        Inline the slices with LLM
        """
        slices = set(state.get_slice_tree())
        with open(self.inline_prompt_file, "r") as f:
            dump_config_dict = json.load(f)
        role = dump_config_dict["system_role"].replace("<LANGUAGE>", self.language)
        solve_model = LLM(self.model_name, self.temp, role)
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
        Fetch the detection prompt, leaving the placeholders <FUNCTION> and <SRC_NAME> to be filled
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
