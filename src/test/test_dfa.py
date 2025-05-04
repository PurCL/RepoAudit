import sys
from os import path
from pathlib import Path
import json
import time
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from tstool.src_extractor.Cpp.Cpp_NPD_extractor import Cpp_NPD_Extractor
from tstool.src_extractor.Cpp.Cpp_MLK_extractor import Cpp_MLK_Extractor
from tstool.src_extractor.Cpp.Cpp_UAF_extractor import Cpp_UAF_Extractor
from repoaudit import RepoAudit

BASE_DIR = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))


class TestDFScan:
    ############### Test DFScan ###############
    def __init__(self, language, bug_type):
        self.language = language
        self.bug_type = bug_type
        self.test_cases = set()
        self.test_case_num = 0

    def run(self):
        start_time = time.time()
        self.analyze()
        self.validate()
        print("====================Test Result====================")
        print(f"Language: {self.language}")
        print(f"Bug Type: {self.bug_type}")
        print(f"Execution Time: {time.time() - start_time:.2f} seconds")
        print(f"Detected Test Cases: {self.test_case_num-len(self.test_cases)} / {self.test_case_num}")
        print("Missing Test Cases: ", self.test_cases)


    def analyze(self):
        seed_path = f"{BASE_DIR}/result/src_extract/{self.bug_type}/{self.language}_toy/seed_result.json"
        project_path = f"{BASE_DIR}/benchmark/{self.language}/toy"

        if self.language == "Cpp":
            for file in Path(f"{project_path}/{self.bug_type}").rglob("*.cpp"):
                self.test_cases.add(str(file))
            self.test_case_num = len(self.test_cases)
            if self.bug_type == "NPD":
                extractor = Cpp_NPD_Extractor(project_path, self.language, seed_path)
            elif self.bug_type == "MLK":
                extractor = Cpp_MLK_Extractor(project_path, self.language, seed_path)
            elif self.bug_type == "UAF":
                extractor = Cpp_UAF_Extractor(project_path, self.language, seed_path)
            else:
                raise ValueError("Invalid bug type")
        else:
            raise ValueError("Invalid language")
        extractor.run()

        batch_scan = RepoAudit(
            seed_spec_file=seed_path,
            project_path=project_path,
            language=self.language,
            inference_model_name="claude-3.7",
            temperature=0.0,
            scanners=["DFscan"],
            bug_type=self.bug_type,
            boundary=3,
            max_workers=5
        )

        batch_scan.start_batch_scan()

    def validate(self):
        result_dir = f"{BASE_DIR}/result/DFscan-claude-3.7/{self.bug_type}/{self.language}_toy/"
        if Path(result_dir).exists():
            timestamps = [d.name for d in Path(result_dir).iterdir() if d.is_dir()]
            if not timestamps:
                print("No results found.")
                return 
            timestamps.sort(reverse=True)
            timestamp = timestamps[0]

        result_path = f"{BASE_DIR}/result/DFscan-claude-3.7/{self.bug_type}/{self.language}_toy/{timestamp}/bug_info.json"
        if not Path(result_path).exists():
            print("Result file does not exist.")
            return 
        with open(result_path, 'r') as f:
            results = json.load(f)
        
        for _, item in results.items():
            paths = item["Path"]
            vali_llm = item["Vali_LLM"]
            if vali_llm == "True":
                file_name = paths[0]["file_name"]
                for path in paths:
                    if path["file_name"] != file_name:
                        print(f"Cross-file Bug Trace: {file_name} -> {path['file_name']}")
                        break
                self.test_cases.discard(file_name)
        

if __name__ == "__main__":
    test_Cpp_NPD = TestDFScan("Cpp", "NPD")
    test_Cpp_NPD.run()