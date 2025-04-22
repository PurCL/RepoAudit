import streamlit as st
import sys
from pathlib import Path
import json

# Add the parent directory to the system path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Language dictionary
language_dict = {
    "Cpp": "cpp"
}

# Base path for results
BASE_PATH = Path(__file__).resolve().parents[2]

# Function to get results
def get_results(language="C", scanner="bugscan", model="claude-3.7", bug_type="NPD") -> list:
    result_dir = Path(f"{BASE_PATH}/result/{scanner}-{model}/{bug_type}")
    if not result_dir.exists():
        return []
    projects = []
    for dir in result_dir.iterdir():
        if dir.is_dir():
            lang, project_name = dir.name.split("_")
            if lang == language:
                projects.append(project_name)
    return projects

# Function to display the Home page
def display_home():
    st.title("Welcome to RepoAudit")
    st.markdown("""
        RepoAudit is a tool for analyzing code repositories and detecting bugs.
        Use the sidebar to navigate between different functionalities.
    """)

# Function to display the Results page
def display_results():
    st.title("Analysis Results")
    
    # 0. Language Selection
    language = st.selectbox(
        "Select Language",
        language_dict.keys(),
        help="Select the language"
    )
    
    # 1. Scanner Selection
    scanner = st.selectbox(
        "Select Scanner",
        ["bugscan", "DFscan"],
        help="Select the scanner"
    )

    # 2. Model Selection
    model = st.selectbox(
        "Select Model",
        ["claude-3.5", "claude-3.7", "o3-mini", "gpt-4o", "gpt-4-turbo", "gpt-4o-mini", "deepseek-local", "deepseek-chat", "deepseek-reasoner", "gemini"],
        help="Select the model"
    )

    scanner_dir = f"{BASE_PATH}/result/{scanner}-{model}"
    if not Path(scanner_dir).exists():
        st.info(f"No results available for the {scanner} with {model}.")
        return
    bug_types = []
    for dir in Path(f"{BASE_PATH}/result/{scanner}-{model}").iterdir():
        if dir.is_dir():
            bug_types.append(dir.name)
    # 3. Bug Type Selection
    bug_type = st.selectbox(
        "Select Bug Type",
        bug_types,
        help="Select the type of bugs to analyze"
    )

    # 4. Project Selection
    projects = get_results(language, scanner, model, bug_type)
    project_name = st.selectbox(
        "Select Project",
        projects,
        help="Choose a project"
    )

    # 5. Timestamp Selection only if a project is selected
    if project_name:
        result_dir = f"{BASE_PATH}/result/{scanner}-{model}/{bug_type}/{language}--{project_name}"
        if Path(result_dir).exists():
            timestamps = [d.name for d in Path(result_dir).iterdir() if d.is_dir()]
            timestamps.sort(reverse=True)
            selected_timestamp = st.selectbox(
                "Select Timestamp",
                timestamps,
                help="Choose a timestamp"
            )
        else:
            st.info("Result directory does not exist for the selected project.")
            return

        result_path = f"{BASE_PATH}/result/{scanner}-{model}/{bug_type}/{language}--{project_name}/{selected_timestamp}/detect_info.json"

        if Path(result_path).exists():
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Show All Results"):
                    with open(result_path, 'r') as f:
                        results = json.load(f)
                    st.session_state.analysis_results = results
            with col2:
                if st.button("Show True Labeled Results"):
                    with open(result_path, 'r') as f:
                        all_results = json.load(f)
                        # Filter results to keep only TP items
                        tp_results = {}
                        for key, item in all_results.items():
                            vali_result = item["is_human_confirmed_true"] if item["is_human_confirmed_true"] != "unknown" else "False"
                            if vali_result == "True":
                                tp_results[key] = item
                    st.session_state.analysis_results = tp_results
            with col3:
                pass
        else:
            st.info("No analysis results available. Please run analysis first.")
    else:
        st.info("Please select a project to view results.")
        
    if st.session_state.analysis_results:
        results = st.session_state.analysis_results
        for key, item in results.items():
            with st.expander(item["buggy_value"]):
                paths = item["relevant_functions"]
                explanations = item["explanation"]
    
                st.markdown("---")
                # if len(explanations) > 1:
                #     explanations_markdown = "\n".join([f"- {exp.strip()}" for exp in explanations if exp.strip()])
                # else:
                #     explanations_markdown = explanations[0]
                st.markdown("**Explanation:**")
                st.text(explanations)
                st.write("**Human Validation Result:**", item["is_human_confirmed_true"])

                validation_key = f"validation_{key}"
                if validation_key not in st.session_state.bug_validations:
                    st.session_state.bug_validations[validation_key] = item["is_human_confirmed_true"] if item["is_human_confirmed_true"] != "unknown" else "unknown"
                
                st.write("**Bug Validation:**")
                col1, col2 = st.columns(2)
                with col1:
                    validation = st.radio(
                        "Is this bug true positive or false positive?",
                        options=["True", "False", "unknown"],
                        key=validation_key,
                        horizontal=True,
                        index=["True", "False", "unknown"].index(st.session_state.bug_validations[validation_key])
                    )
                
                    if validation != st.session_state.bug_validations.get(validation_key):
                        st.session_state.bug_validations[validation_key] = validation
                with col2:
                    if st.button("Save", key=f"save_{key}", use_container_width=True):
                        item["is_human_confirmed_true"] = validation
                        with open(result_path, 'r') as f:
                            temp_results = json.load(f)
                        temp_results[key]["is_human_confirmed_true"] = validation
                        with open(result_path, 'w') as f:
                            json.dump(temp_results, f, indent=4)

                if st.button(
                    "Show Function Content" if not st.session_state.show_function.get(key) 
                    else "Hide Function Content", 
                    key=key
                ):
                    st.session_state.show_function[key] = \
                        not st.session_state.show_function.get(key, False)
                
                if st.session_state.show_function.get(key):
                    for path in paths:
                        function_name = path["function_name"]
                        function_code = path["function_code"]
                        file_name = path["file_name"]
                        st.write(f"**Function: `{function_name}`**")
                        st.write(f"- File: `{file_name}`")
                        st.code(function_code, language=language_dict[language], line_numbers=True)
            
        st.download_button(
            "Download Results",
            data=json.dumps(results, indent=2),
            file_name="detect_info.json",
            mime="application/json"
        )

# Main function to handle navigation
def main():
    st.set_page_config(
        layout="wide",  # Use wide layout instead of centered
        initial_sidebar_state="expanded"
    )
        
    if 'show_function' not in st.session_state:
        st.session_state.show_function = {}
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'bug_validations' not in st.session_state:
        st.session_state.bug_validations = {}

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Results"])

    if page == "Home":
        display_home()
    elif page == "Results":
        display_results()

if __name__ == "__main__":
    main()
