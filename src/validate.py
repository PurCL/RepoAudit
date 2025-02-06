import re
import os
import json
import argparse
import tree_sitter
from tqdm import tqdm
from pathlib import Path
from tree_sitter import Language

from parser.program_parser import *
from parser.ts_transform import *
from utility.function import *
from LMAgent import df_validator


def parse_report(information, language_setting="C"):
    parser = tree_sitter.Parser()
    cwd = Path(__file__).resolve().parent.absolute()
    TSPATH = cwd / "../lib/build/"
    language_path = TSPATH / "my-languages.so"

    if language_setting == "C":
        language = Language(str(language_path), "c")
    elif language_setting == "C++":
        language = Language(str(language_path), "cpp")
    parser.set_language(language)

    result = {
        "Path": [],
        "Explanation": [],
        "Functions": [],
    }

    # extract Explanation
    explanations = information["Explanation"].split("\n")
    for i, explanation in enumerate(explanations):
        result["Explanation"].append(f"{i+1}. {explanation}")

    # extract Path
    source_pattern = r"Source:\s*`([^`]+)`.*?Function:"
    source_matches = re.findall(source_pattern, information["Path"])

    # extract source line number
    src_line_pattern = "SRC:\s*(?P<src_line>\d+)"
    src_line_matches = re.findall(src_line_pattern, information["SrcSinkPath"]) 

    # extract functions
    function_file_pattern = r"Function:\s*`([^`]+)`.*?File:\s*([^>]+)"
    matches = re.findall(function_file_pattern, information["Path"])
    for i, match in enumerate(matches):
        function_name, file = match
        with open(file, "r") as f:
            file_code = f.read()
        tree = parser.parse(bytes(file_code, "utf8"))
        function = parse_function_body(file_code, function_name, tree, int(src_line_matches[i]))
        result["Functions"].append(function.lined_code_without_comments)
        path = f"`{source_matches[i]}` at line {function.file_line2function_line(int(src_line_matches[i]))} in the function `{function_name}`"
        result["Path"].append(path)

    return result


def parse_function_body(source_code:str, tgt_function_name, tree:tree_sitter.Tree, src_line: int) -> Function:
    """
    Parse the function body of the given function name
    """
    all_function_definition_nodes = TSAnalyzer.find_nodes_by_type(tree.root_node, "function_definition")         
    
    for node in all_function_definition_nodes:
        header = TSAnalyzer.find_nodes_by_type(node, "function_declarator")[0]
        function_name = ""
        for sub_node in header.children:
            if sub_node.type == "identifier":
                function_name = source_code[sub_node.start_byte:sub_node.end_byte]
                break
            elif sub_node.type == "qualified_identifier":
                qualified_function_name = source_code[sub_node.start_byte:sub_node.end_byte]
                function_name = qualified_function_name.split("::")[-1]

        if function_name == "" or function_name != tgt_function_name:
            continue
        start_line_number = source_code[: node.start_byte].count("\n") + 1
        end_line_number = source_code[: node.end_byte].count("\n") + 1
        if start_line_number > src_line or end_line_number < src_line:
            print(f"Start line: {start_line_number}, End line: {end_line_number}, Src line: {src_line}")
            continue

        function_body = source_code[node.start_byte:node.end_byte]
        function = Function(0, function_name, function_body, start_line_number, end_line_number, node, "")

        # remove comments in function body
        nodes = TSAnalyzer.find_nodes_by_type(node, "comment")
        for node in nodes:
            comment = source_code[node.start_byte : node.end_byte]
            function_body = function_body.replace(
                comment, "\n" * comment.count("\n")
            )
        function.code_without_comments = function_body

        # attach line number
        function_body_lines = function_body.split("\n")
        for i, line in enumerate(function_body_lines):
            function_body_lines[i] = f"{i+1}. {line}"
        function_body = "\n".join(function_body_lines)
        function.lined_code_without_comments = function_body
        return function


def validate(report_path, output_path, model_name):
    bug_type = report_path.split("/")[-3]
    bug_type_map = {
        "NPD": "Null Pointer Dereference",
        "UAF": "Use After Free",
        "ML": "Memory Leak",
    }
    lang_project_name = report_path.split("/")[-2]
    language = lang_project_name.split("_")[0]
    project_name = "_".join(lang_project_name.split("_")[1:])

    validator = df_validator.DataFlowValidator(
        prompt_file=f"prompt/{bug_type}/validation_prompt.json",
        model_name=model_name,
        temp=0.0,
        language=language,
        bug_type=bug_type_map[bug_type],
    )
    print(f"Processing {project_name}")

    with open(report_path, "r") as f:
        report = json.load(f)
    
    vali_result = {}
    for key, value in report.items():
        info = value[0]
        result = parse_report(info, language)
        path = " --> ".join(result["Path"])
        explanation = "\n".join(result["Explanation"])
        function = "\n\n".join(result["Functions"])

        predict = validator.validate_with_LLM(path, explanation, function)
        info[f"Vali_{model_name}"] = "TP" if predict else "FP"
        vali_result[key] = info

        if "Type" not in info:
            continue
        ground_truth = info["Type"]
        predict = info[f"Vali_{model_name}"]
        if ground_truth != predict:
            print(f"Ground Truth: {ground_truth}, Model Prediction: {predict}")
            print(f"Path: {path}")
            print(f"Explanation: {explanation}")
            print(f"Function: {function}")
            print()
    
    with open(output_path, "w") as f:
        json.dump(vali_result, f, indent=4)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report-path",
        type=str,
        help="Specify the report path",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        help="Specify the output path",
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
        "--single",
        action="store_true",
        help="Specify if validate a single report, other wise validate all reports of a bug type",
    )
    parser.add_argument(
        "--report-dir",
        default="../result/NPD",
        help="Specify the report directory",
    )
    args = parser.parse_args()

    single = args.single
    if single:
        report_path = args.report_path
        output_path = args.output_path
        model_name = args.inference_model
        validate(report_path, output_path, model_name)
    else:
        model_name = args.inference_model
        report_dir = args.report_dir
        for dir in os.listdir(report_dir):
            language = dir.split("_")[0]
            project_name = "_".join(dir.split("_")[1:])
            print(f"Processing {language} {project_name}")
            report_path = os.path.join(report_dir, dir, "bug_report.json")
            output_path = os.path.join(report_dir, dir, f"vali_{model_name}.json")
            validate(report_path, output_path, model_name)
        
        
    
