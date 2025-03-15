import streamlit as st

def main():
    st.set_page_config(
        layout="wide",  # Use wide layout instead of centered
        initial_sidebar_state="expanded"
    )

    st.title("RepoAudit")
    
    # 主页面的内容
    st.markdown("""
    ## Introduction
    RepoAudit is a repo-level bug detector for data-flow bugs. Currently it supports the detection of 3 types of bug: Null Pointer Dereference (NPD), Memory Leak (MLK) and Use After Free (UAF). It leverages [LLMSCAN](https://github.com/PurCL/LLMSCAN) to parse the codebase and use LLM to simulate the program's execution to analyze the data-flow facts starting with the designated source points.
                        
    ## Features
    - Compilation Free Analysis of C/C++ Code
    - Multiple Bug Type Detection
    - Detailed Bug Reports
    - Function Content Visualization
    """)

if __name__ == "__main__":
    main()