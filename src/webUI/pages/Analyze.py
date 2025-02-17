import streamlit as st
import tempfile
import os
import sys
import json
import re
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from scan import BatchScan
from parser.ML_extractor import *
from parser.NPD_extractor import *
from parser.UAF_extractor import *


def get_available_projects(language="C"):
    benchmark_path = Path(__file__).resolve().parents[3] / "benchmark"
    if not benchmark_path.exists():
        return []
    for dir in benchmark_path.iterdir():
        if dir.is_dir() and dir.name == language:
            return [d.name for d in dir.iterdir() if d.is_dir()]


def parse_source_tuple(source_str: str) -> dict:
    """
    Parse source tuple string using regex.
    Format: ((code, line_start, line_end), ValueType.SRC, filepath)
    
    Returns:
        dict: {
            'name': str,
            'line_num': int,
            'filepath': str
        }
    """
    pattern = r'\(\((.*?),\s*(-?\d+),\s*(\d+)\).*?,\s*(.*?).*?,\s*(.*?)\)'
    
    match = re.search(pattern, source_str)
    if match:
        return {
            'name': match.group(1).strip(),
            'line_num': int(match.group(3)),
            'filepath': match.group(5).strip()
        }
    return None


def main():
    st.set_page_config(
        layout="wide",  # Use wide layout instead of centered
        initial_sidebar_state="expanded"
    )
    
    st.markdown("""
        <style>
        .scrollable-container {
            max-height: 400px;
            overflow-y: auto;
            padding: 1rem;
            background-color: #f0f2f6;
            border-radius: 5px;
            font-family: monospace;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("Project Analysis")

    # 0. Language
    language = st.selectbox(
        "Select Language",
        ["C", "C++"],
        help="Select the language"
    )
    
    # 1. Project name
    projects = get_available_projects(language)
    if not projects:
        st.error("No projects found in benchmark directory")
        return
    
    selected_project = st.selectbox(
        "Select Project",
        projects,
        help="Choose a project from benchmark directory"
    )
    
    # 2. Bug Type 
    bug_type = st.selectbox(
        "Select Bug Type",
        ["NPD", "ML", "UAF"],
        help="Select the type of bugs to analyze"
    )
    
    # 3. Model
    model = st.selectbox(
        "Select Model",
        ["claude", "gpt-4o", "gpt-4-turbo", "gpt-4o-mini", "deepseek-chat", "deepseek-reasoner", "gemini"],
        help="Choose the model for analysis"
    )

    # 4. Source
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
        src_lists = []
        with open(src_file, 'r') as f:
            src_result = json.load(f)
        for src in src_result:
            src_tuple = parse_source_tuple(src)
            if src_tuple:
                src_lists.append(src_tuple)

        # Format sources as text
        sources_html = ["<div class='scrollable-container'>"]
        for idx, source in enumerate(src_lists, 1):
            sources_html.append(
                f"{idx:3d}. {source.get('name', 'N/A')}&nbsp;&nbsp;&nbsp;&nbsp;"
                f"{source.get('filepath', 'N/A').split('/')[-1]}:{source.get('line_num', 'N/A')}<br>"
            )
        sources_html.append("</div>")
        
        # Display sources in scrollable container
        st.write("**Extracted Sources:**")
        st.markdown('\n'.join(sources_html), unsafe_allow_html=True)

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