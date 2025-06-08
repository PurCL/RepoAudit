import streamlit as st
import sys
from pathlib import Path
import json

# Add the parent directory to the system path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Language dictionary
language_dict = {"Cpp": "cpp", "Java": "java", "Go": "go"}

# Base path for results
BASE_PATH = Path(__file__).resolve().parents[1]

# Inject custom styles for enhanced aesthetics
st.markdown(
    """
    <style>
        /* Base font sizing */
        html, body, [class*="css"] {
            font-size: 16px !important;
        }
        /* Page title */
        .stApp h1 {
            font-size: 2.5rem !important;
        }
        /* Section headers */
        .stApp h2 {
            font-size: 2rem !important;
        }
        .stApp h3 {
            font-size: 1.5rem !important;
        }
        /* Sidebar navigation labels */
        .stSidebar .css-1d391kg, .stSidebar .css-ffhzni {
            font-size: 1rem !important;
            font-weight: 600;
        }
        /* Buttons styling */
        .stButton > button {
            font-size: 1rem !important;
            border-radius: 8px;
            padding: 0.3em 0.6em !important;
            min-width: auto !important;
            font-weight: 500;
        }
        .stButton > button:hover {
            background-color: #45a049;
        }
        .stDownloadButton > button {
            font-size: 1rem !important;
            border-radius: 8px;
            padding: 0.6em 1.2em !important;
            font-weight: 500;
        }
        .stDownloadButton > button:hover {
            background-color: #1976D2;
        }
        /* Radio and select labels */
        .stRadio > div > label,
        .stSelectbox label,
        .stTextInput label {
            font-size: 1rem !important;
            font-weight: 600;
        }
        /* Expander headers */
        .stExpanderHeader {
            font-size: 1.25rem !important;
            font-weight: 600;
            color: #2E3B4E;
        }
        /* Code blocks */
        .stCodeBlock pre {
            font-size: 0.9rem !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)


# Function to get results
def get_results(
    language="Cpp", scanner="bugscan", model="claude-3.7", bug_type="NPD"
) -> list:
    result_dir = Path(f"{BASE_PATH}/result/{scanner}/{model}/{bug_type}")
    if not result_dir.exists():
        return []
    projects = []
    language_dir = result_dir / language
    if language_dir.exists() and language_dir.is_dir():
        for project_dir in language_dir.iterdir():
            if project_dir.is_dir():
                # Check if any timestamp directory contains detect_info.json
                if any(
                    timestamp_dir / "detect_info.json"
                    for timestamp_dir in project_dir.iterdir()
                    if timestamp_dir.is_dir()
                ):
                    projects.append(project_dir.name)
    return projects


# Function to display the Home page
def display_home():
    st.title("Welcome to RepoAudit")
    st.markdown(
        """
**RepoAudit** is a repo-level bug detector for general bugs. Currently, it supports the detection of diverse bug types (such as Null Pointer Dereference, Memory Leak, and Use After Free) in multiple programming languages (including C/C++, Java, Python, and Go). It leverages **LLMSCAN** to parse the codebase and uses **LLM** to mimic the process of manual code auditing.

### Advantages
- **Compilation-Free Analysis**
- **Multi-Lingual Support**
- **Multiple Bug Type Detection**
- **Customization Support**
        """
    )


# Function to display the Results page
def display_results():
    st.title("Analysis Results")
    st.markdown("### Bug Report Dashboard")

    language = st.selectbox("Select Language", language_dict.keys())
    scanner = st.selectbox("Select Scanner", ["bugscan", "dfbscan"])
    model = st.selectbox(
        "Select Model",
        [
            "claude-3.5",
            "claude-3.7",
            "o3-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4o-mini",
            "gpt-4.1-nano",
            "deepseek-local",
            "deepseek-chat",
            "deepseek-reasoner",
            "gemini",
        ],
    )

    scanner_dir = Path(f"{BASE_PATH}/result/{scanner}/{model}")
    if not scanner_dir.exists():
        return

    # Only get bug type directories that have detect_info.json files
    bug_types = [
        d.name
        for d in scanner_dir.iterdir()
        if d.is_dir()
        and (d / language).exists()
        and any(
            (d / language / proj / ts / "detect_info.json").exists()
            for proj in (d / language).iterdir()
            if proj.is_dir()
            for ts in proj.iterdir()
            if ts.is_dir()
        )
    ]
    bug_type = st.selectbox("Select Bug Type", bug_types)
    projects = get_results(language, scanner, model, bug_type)
    project_name = st.selectbox("Select Project", projects)

    if project_name:
        project_dir = Path(
            f"{BASE_PATH}/result/{scanner}/{model}/{bug_type}/{language}/{project_name}"
        )
        if project_dir.exists():
            # Only list timestamps that have detect_info.json files
            timestamps = sorted(
                [
                    d.name
                    for d in project_dir.iterdir()
                    if d.is_dir() and (d / "detect_info.json").exists()
                ],
                reverse=True,
            )
            selected_timestamp = st.selectbox("Select Timestamp", timestamps)
        else:
            return

        result_path = project_dir / selected_timestamp / "detect_info.json"

        if result_path.exists():
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Show All Results"):
                    with open(result_path, "r") as f:
                        st.session_state.analysis_results = json.load(f)
            with col2:
                if st.button("Show True Labeled Results"):
                    with open(result_path, "r") as f:
                        all_results = json.load(f)
                    tp_results = {
                        k: v
                        for k, v in all_results.items()
                        if v.get("is_human_confirmed_true") == "True"
                    }
                    st.session_state.analysis_results = tp_results

    if st.session_state.get("analysis_results"):
        results = st.session_state.analysis_results
        for key, item in results.items():
            tokens = item.get("buggy_value").split(",")

            with st.expander(tokens[-4] + " at Line " + tokens[-3]):
                st.markdown("**Explanation:**")
                st.text(item.get("explanation", ""))
                st.write(
                    "**Human Validation Result:**", item.get("is_human_confirmed_true")
                )

                validation_key = f"validation_{key}"
                if validation_key not in st.session_state.bug_validations:
                    st.session_state.bug_validations[validation_key] = "unknown"

                st.write("**Bug Validation:**")
                col1, col2 = st.columns(2)
                with col1:
                    validation = st.radio(
                        "Is this bug true positive or false positive?",
                        options=["True", "False", "unknown"],
                        index=2,
                        key=validation_key,
                        horizontal=True,
                    )
                    st.session_state.bug_validations[validation_key] = validation
                with col2:
                    if st.button("Save", key=f"save_{key}", use_container_width=False):
                        item["is_human_confirmed_true"] = validation
                        with open(result_path, "r") as f:
                            temp_results = json.load(f)
                        temp_results[key]["is_human_confirmed_true"] = validation
                        with open(result_path, "w") as f:
                            json.dump(temp_results, f, indent=4)

                toggle_key = f"show_fn_{key}"
                if st.button(
                    (
                        "Show Function Content"
                        if not st.session_state.show_function.get(toggle_key)
                        else "Hide Function Content"
                    ),
                    key=toggle_key,
                ):
                    st.session_state.show_function[toggle_key] = (
                        not st.session_state.show_function.get(toggle_key, False)
                    )

                if st.session_state.show_function.get(toggle_key):
                    files, names, code_snippets = item.get(
                        "relevant_functions", ([], [], [])
                    )
                    for file, name, snippet in zip(files, names, code_snippets):
                        st.markdown("---")
                        st.markdown(f"**Function: `{name}`**")
                        st.write(f"- File: `{file}`")
                        st.code(
                            snippet,
                            language=language_dict.get("Cpp", "text"),
                            line_numbers=True,
                        )

        st.download_button(
            "Download Results",
            data=json.dumps(results, indent=2),
            file_name="detect_info.json",
            mime="application/json",
        )


# Main function to handle navigation
def main():
    if "show_function" not in st.session_state:
        st.session_state.show_function = {}
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
    if "bug_validations" not in st.session_state:
        st.session_state.bug_validations = {}

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Results"])

    if page == "Home":
        display_home()
    elif page == "Results":
        display_results()


if __name__ == "__main__":
    main()
