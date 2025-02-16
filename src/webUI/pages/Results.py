import streamlit as st
import sys
from pathlib import Path
import json
import re
import tree_sitter
from tree_sitter import Language

sys.path.append(str(Path(__file__).resolve().parents[2]))
from parser.program_parser import *
from parser.ts_transform import *
from webUI.pages.Analyze import get_available_projects

language_dict = {
    "C": "c",
    "C++": "cpp"
}
BASE_PATH = Path(__file__).resolve().parents[3]

def get_function_content(path, src_sink_path, language_setting="C") -> dict:
    """
    Get the function content from the given path.
    Output: 
    {
        "Function": function_name,
        "Function Body": function_body
    }
    """
    parser = tree_sitter.Parser()
    TSPATH = BASE_PATH / "lib/build/"
    language_path = TSPATH / "my-languages.so"

    if language_setting == "C":
        language = Language(str(language_path), "c")
    elif language_setting == "C++":
        language = Language(str(language_path), "cpp")
    parser.set_language(language)

    result = {}

    # extract source line number
    src_line_pattern = "SRC:\s*(?P<src_line>\d+)"
    src_line_match = re.findall(src_line_pattern, src_sink_path) 

    # extract function name and file path
    function_file_pattern = r"Function:\s*`([^`]+)`.*?File:\s*([^>]+)"
    matches = re.findall(function_file_pattern, path)
    for i, match in enumerate(matches):
        function_name, file = match
        # replace ../ with the actual path
        file = "/".join(file.split("/")[1:])
        file = f"{BASE_PATH}/{file}"
        with open(file, "r") as f:
            file_code = f.read()
            tree = parser.parse(bytes(file_code, "utf8"))
            function_body = parse_function_body(file_code, function_name, tree)
            result[function_name] = function_body

    return result

def parse_function_body(source_code:str, tgt_function_name, tree:tree_sitter.Tree) -> str:
    """
    Parse the function body of the given function name
    """
    all_function_header_nodes = []
    all_function_definition_nodes = TSAnalyzer.find_nodes_by_type(tree.root_node, "function_definition")
    for function_definition_node in all_function_definition_nodes:
        all_function_header_nodes.extend(TSAnalyzer.find_nodes_by_type(function_definition_node, "function_declarator"))               

    for node in all_function_header_nodes:
        function_name = ""
        for sub_node in node.children:
            if sub_node.type == "identifier":
                function_name = source_code[sub_node.start_byte:sub_node.end_byte]
                break
            elif sub_node.type == "qualified_identifier":
                qualified_function_name = source_code[sub_node.start_byte:sub_node.end_byte]
                function_name = qualified_function_name.split("::")[-1]

        if function_name == "" or function_name != tgt_function_name:
            continue
        
        function_node = node.parent

        is_function_definition = True
        while True:
            if function_node.type == "function_definition":
                break
            function_node = function_node.parent
            if function_node is None:
                is_function_definition = False
                break
            if "statement" in function_node.type:
                is_function_definition = False
                break
        if not is_function_definition:
            continue

        function_body = source_code[function_node.start_byte:function_node.end_byte]
    return function_body

def main():
    if 'show_function' not in st.session_state:
        st.session_state.show_function = {}
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'bug_validations' not in st.session_state:
        st.session_state.bug_validations = {}

    st.title("Analysis Results")
    
    # 0. Language选择
    language = st.selectbox(
        "Select Language",
        language_dict.keys(),
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

    result_path = f"{BASE_PATH}/result-{model}/{bug_type}/{language}_{selected_project}/bug_report.json"

    if Path(result_path).exists():
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Show All Results"):
                with open(result_path, 'r') as f:
                    results = json.load(f)
                st.session_state.analysis_results = results
        with col2:
            if st.button("Show TP Results"):
                with open(result_path, 'r') as f:
                    all_results = json.load(f)
                    # Filter results to keep only TP items
                    tp_results = {
                        key: items for key, items in all_results.items() 
                        if any(item.get("Type", item.get("Validate")) == "TP" for item in items)
                    }
                st.session_state.analysis_results = tp_results
        with col3:
            pass
    else:
        st.info("No analysis results available. Please run analysis first.")
        
    if st.session_state.analysis_results:
        results = st.session_state.analysis_results
        # try:
        for key, items in results.items():
            with st.expander(f"Bug in {key}"):
                item = items[0]
                paths = item["Path"].split(" --> ")
                explanations = item["Explanation"].split("\n")
    
                st.markdown("---")
                # Convert paths to markdown list
                paths_markdown = "\n".join([f"- {path.strip()}" for path in paths if path.strip()])
                st.markdown("**Path:**")
                st.markdown(paths_markdown)
                
                # Convert explanations to markdown list
                explanations_markdown = "\n".join([f"- {exp.strip()}" for exp in explanations if exp.strip()])
                st.markdown("**Explanation:**")
                st.markdown(explanations_markdown)
                st.write("**LLM Validation Result:**", item["Validate"])
                if "Type" in item:
                    st.write("**Human Validation Result:**", item["Type"])

                # Add validation radio buttons
                validation_key = f"validation_{key}"
                if validation_key not in st.session_state.bug_validations:
                    st.session_state.bug_validations[validation_key] = item["Type"] if "Type" in item else item["Validate"]
                
                st.write("**Bug Validation:**")
                col1, col2 = st.columns(2)
                with col1:
                    validation = st.radio(
                        "Is this bug true positive or false positive?",
                        options=["TP", "FP", "Unsure"],
                        key=validation_key,
                        horizontal=True,
                        index=["TP", "FP", "Unsure"].index(st.session_state.bug_validations[validation_key])
                    )
                
                    if validation != st.session_state.bug_validations.get(validation_key):
                        st.session_state.bug_validations[validation_key] = validation
                with col2:
                    if st.button("Save", key=f"save_{key}", use_container_width=True):
                        item["Type"] = validation
                        with open(result_path, 'w') as f:
                            json.dump(results, f, indent=4)
                            
                # Show function content
                if st.button(
                    "Show Function Content" if not st.session_state.show_function.get(key) 
                    else "Hide Function Content", 
                    key=key
                ):
                    st.session_state.show_function[key] = \
                        not st.session_state.show_function.get(key, False)
                
                if st.session_state.show_function.get(key):
                    function_contents = get_function_content(item["Path"], item["SrcSinkPath"], language)
                    for function_name, function_content in function_contents.items():
                        st.write(f"**Function: {function_name}**")
                        st.code(function_content, language=language_dict[language], line_numbers=True)
        
        # except Exception as e:
        #     st.error(f"Error occurred: {str(e)}")
            
        st.download_button(
            "Download Results",
            data=json.dumps(results, indent=2),
            file_name="analysis_results.json",
            mime="application/json"
        )


if __name__ == "__main__":
    main()