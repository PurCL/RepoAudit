import argparse
import glob
from agent.metascan import *
from agent.bugscan import *
from agent.DFscan import *
from agent.slicescan import *

from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *

class RepoAudit:
    def __init__(
        self,
        seed_spec_file: str,
        project_path: str,
        language: str,
        inference_model_name: str,
        temperature: float,
        scanners: list,
        bug_type: str,
        call_depth: int,
        max_workers: int
    ):
        """
        Initialize BatchScan object with project details.
        """
        self.seed_spec_file = seed_spec_file
        self.project_path = project_path
        self.language = language if language not in {"C", "Cpp"} else "Cpp"
        self.scanners = scanners
        self.bug_type = bug_type
        self.call_depth = call_depth
        self.max_workers = max_workers

        self.code_in_files = {}
        self.inference_model_name = inference_model_name
        self.temperature = temperature
        self.batch_scan_statistics = {}

        suffixs = []
        if self.language == "Cpp":
            suffixs = ["cpp", "cc", "hpp", "c", "h"]
        elif self.language == "Go":
            suffixs = ["go"]
        elif self.language == "Java":
            suffixs = ["java"]
        elif self.language == "Python":
            suffixs = ["py"]
        else:
            raise ValueError("Invalid language setting")
        
        # Load all files with the specified suffix in the project path
        self.travese_files(project_path, suffixs)

        if self.language == "Cpp":
            self.ts_analyzer = Cpp_TSAnalyzer(self.code_in_files, self.language)
        elif self.language == "Go":
            self.ts_analyzer = Go_TSAnalyzer(self.code_in_files, self.language)
        elif self.language == "Java":
            self.ts_analyzer = Java_TSAnalyzer(self.code_in_files, self.language)
        elif self.language == "Python":
            self.ts_analyzer = Python_TSAnalyzer(self.code_in_files, self.language)
        return


    def start_batch_scan(self) -> None:
        """
        Start the batch scan process.
        """
        project_name = self.language  + "_" + self.project_path.split("/")[-1]

        if "metascan" in self.scanners:
            metascan_pipeline = MetaScanAgent(
                project_name,
                self.language,
                self.ts_analyzer,
                self.inference_model_name,
                self.temperature
            )
            metascan_pipeline.start_scan()
        
        if "bugscan" in self.scanners:
            bugscan_agent = BugScanAgent(
                self.seed_spec_file,
                self.bug_type,
                project_name,
                self.language,
                self.ts_analyzer,
                self.inference_model_name,
                self.temperature,
                self.call_depth,
                self.max_workers
            )
            bugscan_agent.start_scan()

        if "DFscan" in self.scanners:
            DFscan_agent = DFScanAgent(
                self.seed_spec_file,
                project_name,
                self.language,
                self.ts_analyzer,
                self.inference_model_name,
                self.temperature,
                self.bug_type,
                self.call_depth,
                self.max_workers
            )
            DFscan_agent.start_scan()

        if "slicescan" in self.scanners:
            slicescan_agent = SliceScanAgent(
                [],
                True,
                project_name,
                self.language,
                self.ts_analyzer,
                self.inference_model_name,
                self.temperature,
                self.call_depth,
                self.max_workers
            )
            slicescan_agent.start_scan()
            print(slicescan_agent.get_agent_result())



    def travese_files(self, project_path: str, suffixs: List) -> None:
        """
        Traverse all files in the project path.
        """
        for suffix in suffixs:
            for file in glob.glob(f"{project_path}/**/*.{suffix}", recursive=True):
                try:
                    with open(file, "r") as c_file:
                        c_file_content = c_file.read()
                        self.code_in_files[file] = c_file_content
                except:
                    print(f"Error reading file {file}")


def run_dev_mode():
    """
    Run in development mode by parsing arguments and starting the batch scan.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-path",
        type=str,
        help="Specify the project path",
    )
    parser.add_argument(
        "--bug-type",
        choices=["NPD", "MLK", "UAF", "BOF"],
        help="Specify the bug type",
    )
    parser.add_argument(
        "--language",
        choices=[
            "C",
            "Cpp",
            "Java",
            "Go",
            "Python"
        ],
        help="Specify the language",
    )
    parser.add_argument(
        "--inference-model",
        choices=[
            "gpt-4o",
            "gpt-4-turbo",
            "gemini",
            "gpt-4o-mini",
            "o3-mini",
            "claude-3.5",
            "claude-3.7",
            "deepseek-chat",
            "deepseek-reasoner"
        ],
        help="Specify LLM model for Inference",
    )
    parser.add_argument(
        "--global-temperature",
        choices=["0.0", "0.5", "0.7", "1.0", "1.5", "1.7", "2.0"],
        help="Specify the temperature",
    )
    parser.add_argument(
        "--scanners",
        nargs='+',
        choices=["metascan", "bugscan", "DFscan", "slicescan"],
        help="Specify which scanners to invoke",
    )
    parser.add_argument(
        "--seed-spec-file",
        type=str,
        help="Specify the seed spec file",
    )
    parser.add_argument(
        "--call-depth",
        type=int,
        help="Specify the retrieval call depth",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Specify the number of workers",
    )

    args = parser.parse_args()
    project_path = args.project_path
    language = args.language
    inference_model = args.inference_model
    global_temperature = float(args.global_temperature)
    scanners = args.scanners if args.scanners else []
    seed_spec = args.seed_spec_file
    bug_type = args.bug_type
    call_depth = args.call_depth
    max_workers = args.max_workers

    print(seed_spec)

    batch_scan = RepoAudit(
        seed_spec,
        project_path,
        language,
        inference_model,
        global_temperature,
        scanners,
        bug_type,
        call_depth,
        max_workers
    )
    batch_scan.start_batch_scan()


if __name__ == "__main__":
    run_dev_mode()
