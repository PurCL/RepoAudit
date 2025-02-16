# RepoScan

RepoAudit is a repo-level bug detector for data-flow bugs. Currently it supports the detection of 3 types of bug: Null Pointer Dereference (NPD), Memory Leak (MLK) and Use After Free (UAF). It leverages [LLMSCAN](https://github.com/PurCL/LLMSCAN) to parse the codebase and use LLM to simulate the program's execution to analyze the data-flow facts starting with the designated source points.


## Features
- Compilation Free Analysis of C/C++ Code
- Multiple Bug Type Detection
- Detailed Bug Reports
- Convinent WebUI Interface


## Installation

1. Clone the repository:

   ```sh
   git clone git@github.com:PurCL/RepoScan.git --recursive
   cd RepoScan
   ```

2. Install the required dependencies:

   ```sh
   pip install -r requirements.txt
   ```

3. Ensure you have the Tree-sitter library and language bindings installed:

   ```sh
   cd lib
   python build.py
   ```

4. Configure LLM API keys. For Claude3.5, we use the model hosted by Amazon Bedrock.

   ```sh
   export OPENAI_API_KEY=xxxxxx >> ~/.bashrc
   export DEEPSEEK_API_KEY=xxxxxx >> ~/.bashrc
   ```



## Quick Start

1. Prepare the project that you want to analyze and store them in directory `banchmark`. Here we've provided two projects for testing

   * sofa-pbrpc (NPD)
   * memcached (ML)


2. (Option1) Command Line: Run the test script

   ```sh
   cd src
   
   # For memory leak bug detection
   ./test_ML.sh
   
   # For null pointer dereference bug detection
   ./test_NPD.sh
   ```

3. (Option2) WebUI:

   ```sh
   cd src/webUI
   streamlit run Home.py
   ```

The extracted source and sink lists are dumped in the directory `result`. The detection results are dumped in the directory `result-{model_name}`.



## Result Format

```json
    "Function level buggy trace": [
        {
            "Path": "Path sensitive buggy trace",
            "Explanation": "The explanation of the data-flow facts.",
            "SrcSinkPath": "The line number of source and sink point in each function.",
            "Validate": "The validation result of LLM-based validator."
        }
    ],
```



## More

For more details, please refer this paper: [RepoAudit: An Autonomous LLM-Agent for Repository-Level Code Auditing](https://arxiv.org/pdf/2501.18160v2)