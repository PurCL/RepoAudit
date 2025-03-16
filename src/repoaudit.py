import argparse
import glob
from agent.metascan import *
from agent.bugscan import *
from agent.DFscan import *
from agent.slicescan import *

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
        boundary: int,
        max_workers: int
    ):
        """
        Initialize BatchScan object with project details.
        """
        self.seed_spec_file = seed_spec_file
        self.project_path = project_path
        self.language = language
        self.scanners = scanners
        self.bug_type = bug_type
        self.boundary = boundary
        self.max_workers = max_workers

        self.all_files = {}
        self.inference_model_name = inference_model_name
        self.temperature = temperature
        self.batch_scan_statistics = {}

        suffixs = []
        if self.language == "C":
            suffixs = ["c", "h"]
        elif self.language == "Cpp":
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

    def start_batch_scan(self) -> None:
        """
        Start the batch scan process.
        """
        project_name = self.language  + "_" + self.project_path.split("/")[-1]

        if "metascan" in self.scanners:
            metascan_pipeline = MetaScanAgent(
                project_name,
                self.language,
                self.all_files,
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
                self.all_files,
                self.inference_model_name,
                self.temperature,
                self.boundary,
                self.max_workers
            )
            bugscan_agent.start_scan()

        if "DFscan" in self.scanners:
            DFscan_agent = DFScanAgent(
                self.seed_spec_file,
                project_name,
                self.language,
                self.all_files,
                self.inference_model_name,
                self.temperature,
                self.bug_type,
                self.boundary,
                self.max_workers
            )
            DFscan_agent.start_scan()

        if "slicescan" in self.scanners:
                # def __init__(self,
                #  seed_values: List[Value],
                #  is_backward: bool,
                #  project_name: str,
                #  language: str,
                #  code_in_projects: Dict[str, str],
                #  model_name: str,
                #  temperature: float,
                #  call_depth: int = 1,
                #  max_workers: int = 1
                #  ) -> None:
            slicescan_agent = SliceScanAgent(
                [],
                True,
                project_name,
                self.language,
                self.all_files,
                self.inference_model_name,
                self.temperature,
                self.boundary,
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
                        self.all_files[file] = c_file_content
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
        "--boundary",
        type=int,
        help="Specify the retrieval boundary",
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
    boundary = args.boundary
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
        boundary,
        max_workers
    )
    batch_scan.start_batch_scan()


if __name__ == "__main__":
    run_dev_mode()
