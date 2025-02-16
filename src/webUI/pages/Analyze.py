import streamlit as st
import tempfile
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from scan import BatchScan
from parser.ML_extractor import *
from parser.NPD_extractor import *
from parser.UAF_extractor import *


def get_available_projects(language="C"):
    """获取benchmark目录下的所有项目"""
    benchmark_path = Path(__file__).resolve().parents[3] / "benchmark"
    if not benchmark_path.exists():
        return []
    for dir in benchmark_path.iterdir():
        if dir.is_dir() and dir.name == language:
            return [d.name for d in dir.iterdir() if d.is_dir()]

def main():
    st.title("Project Analysis")

    # 0. Language选择
    language = st.selectbox(
        "Select Language",
        ["C", "C++"],
        help="Select the language"
    )
    
    # 1. Project选择
    projects = get_available_projects(language)
    if not projects:
        st.error("No projects found in benchmark directory")
        return
    
    selected_project = st.selectbox(
        "Select Project",
        projects,
        help="Choose a project from benchmark directory"
    )
    
    # 2. Bug Type选择
    bug_type = st.selectbox(
        "Select Bug Type",
        ["NPD", "ML", "UAF"],
        help="Select the type of bugs to analyze"
    )
    
    # 3. Model选择
    model = st.selectbox(
        "Select Model",
        ["claude", "gpt-4o", "gpt-4-turbo", "gpt-4o-mini", "deepseek-chat", "deepseek-reasoner", "gemini"],
        help="Choose the model for analysis"
    )

    # 4. Source输入
    source = st.text_input(
        "Source",
        value="",
        help="Enter the source to analyze, split with ', '. Default: \n - NPD: NULL value. \n - ML: Defaylt memory allocation API. \n - UAF: Default memory free API."
    )
    
    # Extract Source Button
    if selected_project and bug_type and model:
        base_path = Path(__file__).resolve().parents[3]
        src_file = f"{base_path}/result/{bug_type}/{language}_{selected_project}/src_result.json"
        sink_file = f"{base_path}/result/{bug_type}/{language}_{selected_project}/sink_result.json"
        analyze_prompt_file = f"{base_path}/src/prompt/{bug_type}/analysis_prompt_reach.json"
        validate_prompt_file = f"{base_path}/src/prompt/{bug_type}/validation_prompt.json"
        project_path = f"{base_path}/benchmark/{language}/{selected_project}"
        inference_model = model
        source = source.strip()
        src_API = source.split(", ") if source else []

        if st.button("Extract Source"):
            try:
                with st.spinner('Extracting...'):
                    # store the config in session state
                    st.session_state.analysis_config = {
                        "language": language,
                        "project": selected_project,
                        "bug_type": bug_type,
                        "model": model,
                        "source": source
                    }

                    # extract source
                    if bug_type == "ML":
                        extractor = ML_Extractor(project_path, language, False, src_API, []) 
                    elif bug_type == "NPD":
                        extractor = NPD_Extractor(project_path, language, False, src_API, []) 
                    elif bug_type == "UAF":
                        extractor = UAF_Extractor(project_path, language, False, src_API, [])
                    
                    extractor.run()

            except Exception as e:
                st.error(f"Error during extracting source: {str(e)}")      

    # Start Analysis Button
    if Path.exists(Path(src_file)):
        if st.button("Start Analysis"):
            try:
                with st.spinner('Analyzing...'):
                    # start analyze
                    batch_scan = BatchScan(
                        src_file,
                        sink_file,
                        analyze_prompt_file,
                        validate_prompt_file,
                        project_path,
                        language,
                        inference_model,
                        temperature=0.0,
                        is_fscot=True,
                        scanners="bugscan",
                        bug_type=bug_type,
                        sink_functions=[],
                    )
                    batch_scan.start_batch_scan()
                    
                st.success("Analysis Complete!")
                st.info("View results in the Results page")
                
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
    else:
        st.info("Please first extract source and then start analysis")

    # Display current configuration
    with st.expander("Current Configuration"):
        st.json({
            "Language": language,
            "Project": selected_project,
            "Bug Type": bug_type,
            "Model": model,
            "Source": source
        })

if __name__ == "__main__":
    main()