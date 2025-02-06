import os
import argparse
from pathlib import Path
import glob
from pipeline.apiscan import *
from pipeline.metascan import *
from pipeline.bugscan import *

class BatchScan:
    def __init__(
        self,
        src_spec_file: str,
        sink_spec_file: str,
        analyze_prompt_file: str,
        validate_prompt_file: str,
        project_path: str,
        language: str,
        inference_model_name: str,
        temperature: float,
        is_fscot: bool,
        scanners: list,
        bug_type: str,
        sink_functions
    ):
        """
        Initialize BatchScan object with project details.
        """
        self.src_spec_file = src_spec_file
        self.sink_spec_file = sink_spec_file
        self.analyze_prompt_file = analyze_prompt_file
        self.validate_prompt_file = validate_prompt_file
        self.project_path = project_path
        self.language = language
        self.scanners = scanners
        self.bug_type = bug_type
        self.sink_functions = sink_functions

        self.all_files = {}
        self.inference_model_name = inference_model_name
        self.temperature = temperature
        self.is_fscot = is_fscot
        self.batch_scan_statistics = {}

        suffixs = []
        if self.language == "C":
            suffixs = ["c", "h"]
        elif self.language == "C++":
            suffixs = ["cpp", "cc", "hpp", "c", "h"]
        elif self.language == "Java":
            suffixs = ["java"]
        elif self.language == "Python":
            suffixs = ["py"]
        
        # Load all files with the specified suffix in the project path
        self.travese_files(project_path, suffixs)

        print(len(self.all_files))

    def start_batch_scan(self) -> None:
        """
        Start the batch scan process.
        """
        project_name = self.language  + "_" + self.project_path.split("/")[-1]

        if "metascan" in self.scanners:
            metascan_pipeline = MetaScanPipeline(
                project_name,
                self.language,
                self.all_files,
                self.inference_model_name,
                self.temperature
            )
            metascan_pipeline.start_scan()

        if "bugscan" in self.scanners:
            bugscan_pipeline = BugScanPipeline(
                self.src_spec_file,
                self.sink_spec_file,
                self.analyze_prompt_file,
                self.validate_prompt_file,
                project_name,
                self.language,
                self.all_files,
                self.inference_model_name,
                self.temperature,
                self.is_fscot,
                self.bug_type,
                self.sink_functions
            )
            bugscan_pipeline.start_scan()


    def travese_files(self, project_path: str, suffixs: List) -> None:
        """
        Traverse all files in the project path.
        """
        for suffix in suffixs:
            for file in glob.glob(f"{project_path}/**/*.{suffix}", recursive=True):
                with open(file, "r") as c_file:
                    c_file_content = c_file.read()
                    self.all_files[file] = c_file_content


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
        choices=["NPD", "ML", "UAF"],
        help="Specify the bug type",
    )
    parser.add_argument(
        "--language",
        choices=[
            "C",
            "C++",
            "Java",
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
            "claude",
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
        "--is-fscot",
        action="store_true",
        help="Specify if FSCOT is enabled",
    )
    parser.add_argument(
        "--scanners",
        nargs='+',
        choices=["metascan", "bugscan"],
        help="Specify which scanners to invoke",
    )
    parser.add_argument(
        "--src-spec-file",
        type=str,
        help="Specify the source spec file",
    )
    parser.add_argument(
        "--sink-spec-file",
        type=str,
        help="Specify the sink spec file",
    )
    parser.add_argument(
        "--analyze-prompt-file",
        type=str,
        help="Specify the prompt file",
    )
    parser.add_argument(
        "--validate-prompt-file",
        type=str,
        help="Specify the prompt file",
    )
    parser.add_argument(
        "--sink-functions",
        nargs='*',
        help="Specify the sink functions",
    )


    args = parser.parse_args()
    project_path = args.project_path
    language = args.language
    inference_model = args.inference_model
    global_temperature = float(args.global_temperature)
    scanners = args.scanners if args.scanners else []
    src_spec = args.src_spec_file
    sink_spec = args.sink_spec_file
    analyze_prompt_file = args.analyze_prompt_file
    validate_prompt_file = args.validate_prompt_file
    is_fscot = args.is_fscot
    bug_type = args.bug_type
    sink_functions = args.sink_functions
    
    print(src_spec)

    batch_scan = BatchScan(
        src_spec,
        sink_spec,
        analyze_prompt_file,
        validate_prompt_file,
        project_path,
        language,
        inference_model,
        global_temperature,
        is_fscot,
        scanners,
        bug_type,
        sink_functions
    )
    print("Starting batch scan...")
    batch_scan.start_batch_scan()


if __name__ == "__main__":
    run_dev_mode()
