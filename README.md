# RepoAudit-Plus

RepoAudit-Plus is a repo-level bug detector for general bugs. Currently it supports the detection of 4 types of bug: Null Pointer Dereference (NPD), Memory Leak (MLK), Use After Free (UAF), and Memory Leak (MLK). It leverages [LLMSCAN](https://github.com/PurCL/LLMSCAN) to parse the codebase and use LLM to simulate the program's execution to analyze the data-flow facts starting with the designated source points. RepoAudit-Plus is a strengthened version of [RepoAudit](https://arxiv.org/pdf/2501.18160).


## Features

- Compilation Free Analysis of C/C++ Code
- Multiple Bug Type Detection
- Detailed Bug Reports
- Convenient WebUI Interface (Todo)


## Installation

1. Clone the repository:

   ```sh
   git clone git@github.com:PurCL/RepoAudit-Plus.git --recursive
   cd RepoAudit-Plus
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



## Architecture

```sh
# In src directory

├── extractor/           # Customized source extractors
├── bugscan.sh           # Main script to start the bug scan
├── prompt/              # Prompt files
├── LMAgent/             # Directory for LMAgent related files, provides two options: from bottom to top analysis and from top to bottom analysis
├── extract.sh           # Script for customized source extraction
├── utility/             # Utility scripts and files
├── pipeline/            # Pipeline scripts for bug detection
│   ├── metascan.py      # Script for metascan functionality
│   ├── neumeric_scan.py # Script for numeric scan functionality
├── scan.py              # Main script for scanning
├── parser/              # Directory for parser scripts
│   ├── base_parser.py   # Base class for program parsers
│   ├── C_parser.py      # Script for parsing C programs
```



## More

For more details, please refer this paper: [RepoAudit: An Autonomous LLM-Agent for Repository-Level Code Auditing](https://arxiv.org/pdf/2501.18160v2)