import argparse
import glob
import sys
from agent.metascan import *
from agent.bugscan import *
from agent.slicescan import *
from agent.dfbscan import *

from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *

from typing import List


default_bugscan_checkers = {
    "Cpp": ["BOF", "MLK", "NPD", "UAF"],
    "Go": ["BOF", "NPD"],
    "Java": ["NPD"],
    "Python": ["NPD"]
}

# TODO
default_dfbscan_checkers = {
    "Cpp": ["MLK", "NPD", "UAF"],
    "Java": ["NPD"]
}

class RepoAudit:
    def __init__(
        self,
        args: argparse.Namespace,
    ):
        """
        Initialize BatchScan object with project details.
        """
        # argument format check
        self.args = args
        is_input_valid, error_messages = self.validate_inputs()
    
        if not is_input_valid:
            print("\n".join(error_messages))
            exit(1)
        
        self.project_path = args.project_path
        self.language = args.language
        self.code_in_files = {}

        self.model_name = args.model_name
        self.temperature = args.temperature
        self.call_depth = args.call_depth
        self.max_workers = args.max_workers

        self.bug_type = args.bug_type
        self.is_reachable = args.is_reachable
        self.is_backward = args.is_backward

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
        self.travese_files(self.project_path, suffixs)

        if self.language == "Cpp":
            self.ts_analyzer = Cpp_TSAnalyzer(self.code_in_files, self.language)
        elif self.language == "Go":
            self.ts_analyzer = Go_TSAnalyzer(self.code_in_files, self.language)
        elif self.language == "Java":
            self.ts_analyzer = Java_TSAnalyzer(self.code_in_files, self.language)
        elif self.language == "Python":
            self.ts_analyzer = Python_TSAnalyzer(self.code_in_files, self.language)
        return

    def start_repo_auditing(self) -> None:
        """
        Start the batch scan process.
        """
        if self.args.scan_type == "metascan":
            metascan_pipeline = MetaScanAgent(
                self.project_path,
                self.language,
                self.ts_analyzer,
                self.model_name,
                self.temperature
            )
            metascan_pipeline.start_scan()
        
        if self.args.scan_type == "bugscan":
            bugscan_agent = BugScanAgent(
                self.bug_type,
                self.project_path,
                self.language,
                self.ts_analyzer,
                self.model_name,
                self.temperature,
                self.call_depth,
                self.max_workers
            )
            bugscan_agent.start_scan()

        if self.args.scan_type == "slicescan":
            slicescan_agent = SliceScanAgent(
                [],
                self.is_backward,
                self.project_path,
                self.language,
                self.ts_analyzer,
                self.model_name,
                self.temperature,
                self.call_depth,
                self.max_workers
            )
            slicescan_agent.start_scan()
            print(slicescan_agent.get_agent_result())

        if self.args.scan_type == "dfbscan":
            dfbscan_agent = DFBScanAgent(
                self.bug_type,
                self.is_reachable,
                self.project_path,
                self.language,
                self.ts_analyzer,
                self.model_name,
                self.temperature,
                self.call_depth,
                self.max_workers
            )
            dfbscan_agent.start_scan()
        return

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
        return

    def validate_inputs(self) -> Tuple[bool, List[str]]:
        err_messages = []
    
        # For each scan type, check required parameters.
        if self.args.scan_type == "bugscan":
            if not self.args.model_name:
                err_messages.append("Error: --model-name is required for bugscan.")
            if not self.args.bug_type:
                err_messages.append("Error: --bug-type is required for bugscan.")
            if self.args.bug_type not in default_bugscan_checkers[self.args.language]:
                err_messages.append("Error: Invalid bug type provided.")
        elif self.args.scan_type == "slicescan":
            if not self.args.is_backward:
                err_messages.append("Error: --is-backward is required for slicescan.")
            if not self.args.model_name:
                err_messages.append("Error: --inference-model-name is required for slicescan.")
        elif self.args.scan_type == "dfbscan":
            if not self.args.model_name:
                err_messages.append("Error: --model-name is required for dfbscan.")
            if not self.args.bug_type:
                err_messages.append("Error: --bug -type is required for dfbscan.")
            if not self.args.is_reachable:
                err_messages.append("Error: --is-reachable is required for dfbscan.")
            if self.args.bug_type not in default_dfbscan_checkers[self.args.language]:
                err_messages.append("Error: Invalid bug type provided.")
        else:
            err_messages.append("Error: Unknown scan type provided.")
        return (len(err_messages) == 0, err_messages)
    
def configure_args():
    parser = argparse.ArgumentParser(
        description="RepoAudit-Plus: Run one of metascan, bugscan, slicescan, or dfbscan."
    )
    parser.add_argument(
        "--scan-type",
        required=True,
        choices=["metascan", "slicescan", "bugscan", "dfbscan"],
        help="The type of scan to perform."
    )
    # Common parameters of metascan, slicescan, bugscan, and dfbscan
    parser.add_argument("--project-path", required=True, help="Project path")
    parser.add_argument("--language", required=True, help="Programming language")

    # Common parameters for slicescan, bugscan, and dfbscan
    parser.add_argument("--model-name", help="The name of LLMs")
    parser.add_argument("--temperature", type=float, default=0.5, help="Temperature for inference")
    parser.add_argument("--call-depth", type=int, default=3, help="Call depth setting")
    parser.add_argument("--max-workers", type=int, default=1, help="Max workers to use for scan")

    # Parameters for slicescan
    parser.add_argument("--is-backward", action="store_true", help="Flag for backward slicing")

    # Common parameters for bugscan and dfbscan
    parser.add_argument("--bug-type", help="Bug type (for bugscan and dfbscan)")

    # Parameters for dfbscan
    parser.add_argument("--is-reachable", action="store_true", help="Flag for bugscan reachability")

    args = parser.parse_args()
    return args


def main() -> None:
    args = configure_args()
    repoaudit = RepoAudit(args)
    repoaudit.start_repo_auditing()
    return


if __name__ == "__main__":
    main()
