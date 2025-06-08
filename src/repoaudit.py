import argparse
import glob
import sys

from agent.metascan import MetaScanAgent
from agent.cgscan import CGScanAgent
from agent.dfbscan import DFBScanAgent

from tstool.analyzer.TS_analyzer import *
from tstool.analyzer.Cpp_TS_analyzer import *
from tstool.analyzer.Go_TS_analyzer import *
from tstool.analyzer.Java_TS_analyzer import *
from tstool.analyzer.Python_TS_analyzer import *

from utility.errors import RAValueError, RepoAuditError
from typing import List


def format_code_with_line_numbers(code: str) -> str:
    """
    Format code with line numbers starting from 1.

    Args:
        code (str): The code snippet to format

    Returns:
        str: Formatted code with line numbers
    """
    lines = code.split("\n")
    max_line_number_width = len(str(len(lines)))
    formatted_lines = []

    for i, line in enumerate(lines, 1):
        line_number = str(i).rjust(max_line_number_width)
        formatted_lines.append(f"{line_number}: {line}")

    return "\n".join(formatted_lines)


default_bugscan_checkers = {
    "Cpp": ["BOF", "MLK", "NPD", "UAF"],
    "Go": ["BOF", "NPD"],
    "Java": ["NPD"],
    "Python": ["NPD"],
}

default_dfbscan_checkers = {
    "Cpp": ["MLK", "NPD", "UAF"],
    "Java": ["NPD"],
    "Python": ["NPD"],
    "Go": ["NPD"],
}


class RepoAudit:
    def __init__(
        self,
        args: argparse.Namespace,
    ):
        """
        Initialize RepoAudit instance with project details.
        """
        # argument format check
        self.args = args
        is_input_valid, error_messages = self.validate_inputs()

        if not is_input_valid:
            print("\n".join(error_messages))
            exit(1)

        self.project_path = args.project_path
        self.language = args.language
        self.code_in_files: Dict[str, str] = {}

        self.model_name = args.model_name
        self.temperature = args.temperature
        self.call_depth = args.call_depth
        self.max_symbolic_workers = args.max_symbolic_workers
        self.max_neural_workers = args.max_neural_workers

        self.seed_selection_model = args.seed_selection_model
        self.slicing_model = args.slicing_model
        self.inlining_model = args.inlining_model
        self.function_detection_model = args.function_detection_model

        self.bug_type = args.bug_type
        self.is_reachable = args.is_reachable
        self.cg_refine = args.cg_refine

        self.include_test_files = args.include_test_files

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
            raise RAValueError("Invalid language setting")

        # Load all files with the specified suffix in the project path
        self.travese_files(self.project_path, suffixs)

        self.ts_analyzer: TSAnalyzer
        if self.language == "Cpp":
            self.ts_analyzer = Cpp_TSAnalyzer(
                self.code_in_files, self.language, self.max_symbolic_workers
            )
        elif self.language == "Go":
            self.ts_analyzer = Go_TSAnalyzer(
                self.code_in_files, self.language, self.max_symbolic_workers
            )
        elif self.language == "Java":
            self.ts_analyzer = Java_TSAnalyzer(
                self.code_in_files, self.language, self.max_symbolic_workers
            )
        elif self.language == "Python":
            self.ts_analyzer = Python_TSAnalyzer(
                self.code_in_files, self.language, self.max_symbolic_workers
            )

        # Initialize the universal agents
        self.metascan_agent = MetaScanAgent(
            self.project_path, self.language, self.ts_analyzer
        )
        self.metascan_agent.start_scan()

        if self.cg_refine:
            self.cgscan_agent = CGScanAgent(
                self.project_path,
                self.language,
                self.metascan_agent,
                self.model_name,
                self.temperature,
                self.max_neural_workers,
            )
            self.cgscan_agent.start_scan()

        return

    def start_repo_auditing(self) -> None:
        """
        Start the batch scan process.
        """
        if self.args.scan_type == "dfbscan":
            self.dfbscan_agent = DFBScanAgent(
                self.bug_type,
                self.is_reachable,
                self.project_path,
                self.language,
                self.ts_analyzer,
                self.model_name,
                self.temperature,
                self.call_depth,
                self.max_neural_workers,
                include_test_files=self.include_test_files,
            )
            self.dfbscan_agent.start_scan()
        return

    def travese_files(self, project_path: str, suffixs: List) -> None:
        """
        Traverse all files in the project path.
        """
        for suffix in suffixs:
            for file in glob.glob(f"{project_path}/**/*.{suffix}", recursive=True):
                if not self.include_test_files:
                    if "test" in file.lower() or "example" in file.lower():
                        continue
                try:
                    with open(file, "r") as source_file:
                        source_file_content = source_file.read()
                        self.code_in_files[file] = source_file_content
                except (IOError, OSError, UnicodeDecodeError) as e:
                    print(f"Error reading file {file}: {e}")
        return

    def validate_inputs(self) -> Tuple[bool, List[str]]:
        err_messages = []

        # For each scan type, check required parameters.
        if self.args.scan_type == "dfbscan":
            if not self.args.model_name:
                err_messages.append("Error: --model-name is required for dfbscan.")
            if not self.args.bug_type:
                err_messages.append("Error: --bug -type is required for dfbscan.")
            if self.args.bug_type not in default_dfbscan_checkers[self.args.language]:
                err_messages.append("Error: Invalid bug type provided.")
        else:
            err_messages.append("Error: Unknown scan type provided.")
        return (len(err_messages) == 0, err_messages)


def configure_args():
    parser = argparse.ArgumentParser(description="RepoAudit-Plus: Run dfbscan")
    parser.add_argument(
        "--scan-type",
        required=True,
        choices=[
            "dfbscan",
        ],
        help="The type of scan to perform.",
    )
    # Common parameters of metascan, slicescan, bugscan, and dfbscan
    parser.add_argument("--project-path", required=True, help="Project path")
    parser.add_argument("--language", required=True, help="Programming language")
    parser.add_argument(
        "--max-symbolic-workers",
        type=int,
        default=10,
        help="Max symbolic workers for parsing-based analysis",
    )

    parser.add_argument("--model-name", help="The name of LLMs")
    parser.add_argument(
        "--temperature", type=float, default=0.5, help="Temperature for inference"
    )
    parser.add_argument("--call-depth", type=int, default=3, help="Call depth setting")
    parser.add_argument(
        "--max-neural-workers",
        type=int,
        default=1,
        help="Max neural workers for prompting-based analysis",
    )

    # Parameters for samplescan
    parser.add_argument(
        "--seed-selection-model", help="The name of LLMs identifying the seed values"
    )
    parser.add_argument("--slicing-model", help="The name of LLMs for slicing")
    parser.add_argument(
        "--inlining-model", help="The name of LLMs for inline bug detection"
    )
    parser.add_argument(
        "--function-detection-model",
        help="The name of LLMs for function-level bug detection",
    )

    # Common for dfbscan
    parser.add_argument("--bug-type", help="Bug type (for bugscan and dfbscan)")

    # Parameters for dfbscan
    parser.add_argument(
        "--is-reachable", action="store_true", help="Flag for bugscan reachability"
    )

    parser.add_argument(
        "--cg-refine",
        action="store_true",
        help="Flag to refine the call graph with LLM",
    )

    # Parameters for skipping analysis of test files in the project
    parser.add_argument(
        "--include-test-files",
        action="store_true",
        help="Flag to include the project's test files into the analysis process",
    )

    args = parser.parse_args()
    return args


def main() -> None:
    try:
        args = configure_args()
        repoaudit = RepoAudit(args)
        repoaudit.start_repo_auditing()
        return
    except RepoAuditError as e:
        print(f"Error caught during RepoAudit: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
