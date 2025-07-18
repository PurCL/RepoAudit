import streamlit as st
import sys
from pathlib import Path
import json

sys.path.append(str(Path(__file__).resolve().parents[2]))

language_dict = {"C": "c", "Cpp": "cpp"}
BASE_PATH = Path(__file__).resolve().parents[3]


def get_results(
    language="C", scanner="DFscan", model="claude-3.7", bug_type="NPD"
) -> list:
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


def main():
    st.set_page_config(
        layout="wide",  # Use wide layout instead of centered
        initial_sidebar_state="expanded",
    )

    if "show_function" not in st.session_state:
        st.session_state.show_function = {}
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
    if "bug_validations" not in st.session_state:
        st.session_state.bug_validations = {}

    st.title("Analysis Results")

    # 0. Language Selection
    language = st.selectbox(
        "Select Language", language_dict.keys(), help="Select the language"
    )

    # 1. Scanner Selection
    scanner = st.selectbox("Select Scanner", ["dfbscan"], help="Select the scanner")

    # 2. Model Selection
    model = st.selectbox(
        "Select Model",
        [
            "claude-3.5",
            "claude-3.7",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4o-mini",
            "deepseek-local",
            "deepseek-chat",
            "deepseek-reasoner",
            "gemini",
        ],
        help="Select the model",
    )

    # 3. Bug Type Selection
    bug_type = st.selectbox(
        "Select Bug Type",
        ["NPD", "ML", "UAF"],
        help="Select the type of bugs to analyze",
    )

    # 4. Project Selection
    projects = get_results(language, scanner, model, bug_type)
    project_name = st.selectbox("Select Project", projects, help="Choose a project")

    # 5. Timestamp Selection only if a project is selected
    if project_name:
        result_dir = (
            f"{BASE_PATH}/result/{scanner}-{model}/{bug_type}/{language}_{project_name}"
        )
        if Path(result_dir).exists():
            timestamps = [d.name for d in Path(result_dir).iterdir() if d.is_dir()]
            timestamps.sort(reverse=True)
            selected_timestamp = st.selectbox(
                "Select Timestamp", timestamps, help="Choose a timestamp"
            )
        else:
            st.info("Result directory does not exist for the selected project.")

        result_path = f"{BASE_PATH}/result/{scanner}-{model}/{bug_type}/{language}_{project_name}/{selected_timestamp}/bug_info.json"

        if Path(result_path).exists():
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Show All Results"):
                    with open(result_path, "r") as f:
                        results = json.load(f)
                    st.session_state.analysis_results = results
            with col2:
                if st.button("Show True Labeled Results"):
                    with open(result_path, "r") as f:
                        all_results = json.load(f)
                        # Filter results to keep only TP items
                        tp_results = {}
                        for key, item in all_results.items():
                            vali_result = (
                                item["Vali_human"]
                                if item["Vali_human"] != ""
                                else "False"
                            )
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
        # try:
        for key, item in results.items():
            with st.expander(f"{key}"):
                paths = item["Path"]
                explanations = item["Explanation"]

                st.markdown("---")
                # Convert explanations to markdown list
                if len(explanations) > 1:
                    explanations_markdown = "\n".join(
                        [f"- {exp.strip()}" for exp in explanations if exp.strip()]
                    )
                else:
                    explanations_markdown = explanations[0]
                st.markdown("**Explanation:**")
                st.markdown(explanations_markdown)
                st.write("**Human Validation Result:**", item["Vali_human"])

                # Add validation radio buttons
                validation_key = f"validation_{key}"
                if validation_key not in st.session_state.bug_validations:
                    st.session_state.bug_validations[validation_key] = (
                        item["Vali_human"] if item["Vali_human"] != "" else "Unsure"
                    )

                st.write("**Bug Validation:**")
                col1, col2 = st.columns(2)
                with col1:
                    validation = st.radio(
                        "Is this bug true positive or false positive?",
                        options=["True", "False", "Unsure"],
                        key=validation_key,
                        horizontal=True,
                        index=["True", "False", "Unsure"].index(
                            st.session_state.bug_validations[validation_key]
                        ),
                    )

                    if validation != st.session_state.bug_validations.get(
                        validation_key
                    ):
                        st.session_state.bug_validations[validation_key] = validation
                with col2:
                    if st.button("Save", key=f"save_{key}", use_container_width=True):
                        item["Vali_human"] = validation
                        with open(result_path, "r") as f:
                            temp_results = json.load(f)
                        temp_results[key][0]["Vali_human"] = validation
                        with open(result_path, "w") as f:
                            json.dump(temp_results, f, indent=4)

                # Show function content
                if st.button(
                    (
                        "Show Function Content"
                        if not st.session_state.show_function.get(key)
                        else "Hide Function Content"
                    ),
                    key=key,
                ):
                    st.session_state.show_function[key] = (
                        not st.session_state.show_function.get(key, False)
                    )

                if st.session_state.show_function.get(key):
                    for path in paths:
                        source = path["source"]
                        src_line = path["src_line"]
                        function_name = path["function_name"]
                        function_code = path["function_code"]
                        file_name = path["file_name"]
                        st.write(f"**Function: `{function_name}`**")
                        st.write(f"- Source: `{source}` at line {src_line}")
                        st.write(f"- File: `{file_name}`")
                        st.code(
                            function_code,
                            language=language_dict[language],
                            line_numbers=True,
                        )

        # except Exception as e:
        #     st.error(f"Error occurred: {str(e)}")

        st.download_button(
            "Download Results",
            data=json.dumps(results, indent=2),
            file_name="bug_info.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
