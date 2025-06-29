import argparse
import glob
from agent.metascan import *
from agent.dfbscan import *

class RepoAudit:
    def __init__(
        self,
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
        self.traverse_files(project_path, suffixs)

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

        if "dfbscan" in self.scanners:
            dfbscan_agent = DFBScanAgent(
                project_name,
                self.language,
                self.all_files,
                self.inference_model_name,
                self.temperature,
                self.bug_type,
                self.boundary,
                self.max_workers
            )
            dfbscan_agent.start_scan()
            
                    
    def traverse_files(self, project_path: str, suffixs: List) -> None:
        """
        Traverse all files in the project path.
        """        
        for root, dirs, files in os.walk(project_path):
            excluded_dirs = {
                # Common
                '.git', '.vscode', '.idea', 'build', 'dist', 'out', 'bin',
                # Python
                '__pycache__', '.pytest_cache', '.mypy_cache', '.coverage', 'venv', 'env',
                # Java
                'target', '.gradle', '.m2', '.settings', 'classes',
                # C++
                'CMakeFiles', '.deps', 'Debug', 'Release', 'obj',
                # Go
                'vendor', 'pkg'
            }
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in excluded_dirs]
            
            for file in files:
                if any(file.endswith(f'.{suffix}') for suffix in suffixs):
                    file_path = os.path.join(root, file)    
                    if not self.include_test_files:
                        if "test" in file_path.lower() or "example" in file_path.lower():
                            continue
                    
                    try:
                        with open(file_path, "r", encoding='utf-8', errors='ignore') as source_file:
                            source_file_content = source_file.read()
                            self.code_in_files[file_path] = source_file_content
                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")
        return


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
        choices=["NPD", "MLK", "UAF"],
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
        "--model-name",
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
        "--temperature",
        choices=["0.0", "0.25", "0.5", "0.75", "1.0"],
        help="Specify the temperature",
    )
    parser.add_argument(
        "--scan-type",
        nargs='+',
        choices=["metascan", "dfbscan"],
        help="Specify which scanners to invoke",
    )
    parser.add_argument(
        "--call-depth",
        type=int,
        help="Specify the retrieval boundary",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=6,
        help="Specify the number of workers",
    )

    args = parser.parse_args()
    project_path = args.project_path
    language = args.language
    inference_model = args.model_name
    global_temperature = float(args.temperature)
    scanners = args.scan_type if args.scan_type else []
    bug_type = args.bug_type
    boundary = args.call_depth
    max_workers = args.max_workers

    batch_scan = RepoAudit(
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
