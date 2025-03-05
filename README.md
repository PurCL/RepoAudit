# RepoAudit-Plus

RepoAudit-Plus is a repo-level bug detector for general bugs. Currently it supports the detection of 4 types of bug: Null Pointer Dereference (NPD), Memory Leak (MLK), Use After Free (UAF), and Buffer Overflow (BOF). It leverages [LLMSCAN](https://github.com/PurCL/LLMSCAN) to parse the codebase and use LLM to simulate the program's execution to analyze the data-flow facts starting with the designated source points. Particularly, RepoAudit-Plus is a strengthened version of [RepoAudit](https://arxiv.org/pdf/2501.18160).


## Features

- Compilation Free Analysis
- Multi-Linguistic Support
- Multiple Bug Type Detection
- Detailed Bug Reports
- Convenient WebUI Interface (TODO)


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
   * zstd (Buffer Overflow)


2. (Option1) Command Line: Run `run.sh` in the all-in-one mode.

   ```sh
   > cd src
   
   # For buffer overflow detection
   > ./run.sh
   ```
   
3. (Option2) Command Line: Run the extractor and scanner separately.

   ```sh
   > cd src
   
   # For buffer overflow detection
   > ./extract.sh

   > ./bugscan.sh
   ```

The extracted source and sink lists are dumped in the directory `result/extract`. The detection results are dumped in the directory `result/detect-{model_name}`.



## Architecture

```sh
# In src directory
├── agent                # Directory containing different agents for different uses
│   ├── bugscan.py       # Bug scanning agent
│   └── metascan.py      # Meta data extractor
├── memory               # Directory containing utilities in the agent memory
│   ├── function.py      # Utility: Program function
│   ├── localvalue.py    # Utility: Local value
│   └── state.py         # Utility: Program state
├── tstool               # Directory containing tree-sitter-based tools
│   ├── analyzer         # Parsing-based analyzers
│   │   ├── C_TS_analyzer.py # Script for parsing and analyzing C programs
│   │   ├── Go_TS_analyzer.py # Script for parsing and analyzing Go programs
│   │   └── TS_analyzer.py    # Base analyzer
│   └── extractor        # Extractors identifying sources and sinks for different bug types
│       ├── C_BOF_extractor.py # Extractor for Buffer Overflow Detection in C programs
│       ├── C_ML_extractor.py  # Extractor for Memory Leak Detection in C programs
│       ├── C_NPD_extractor.py # Extractor for Null Pointer Dereference in C programs
│       └── C_UAF_extractor.py # Extractor for Use-After-Free in C programs
├── llmtool              # Directory for LLM-based analyzers
│   ├── LLM_tool.py      # Base analyzer
│   ├── LLM_utils.py     # Utility class invoking different LLMs
│   ├── backward_slicer.py # Tool for backward slicing
│   └── forward_slicer.py # Tool for forward slicing
├── prompt               # Directory containing prompt templates
│   ├── detection        # Prompts for detection
│   │   └── BOF_prompt.json # Prompt for Buffer Overflow Detection
│   └── llmtool          # Prompts for LLM-based analysis
│       ├── backward_prompt.json # Prompt for backward slicing
│       ├── forward_prompt.json # Prompt for forward slicing
│       └── inline_prompt.json   # Prompt for function inlining
├── repoaudit.py         # Entry of RepoAudit
├── bugscan.sh           # Main script to start the bug scan
└── extract.sh           # Main script to start the extraction of sensitive values as sources
├── run.sh               # Main script to run RepoAudit
```



## More

The technical report/paper of RepoAudit-Plus has not been ready. 
For more information, 
please refer this paper: [RepoAudit: An Autonomous LLM-Agent for Repository-Level Code Auditing](https://arxiv.org/pdf/2501.18160v2).
We will release the paper of RepoAudit-Plus as soon as possible.