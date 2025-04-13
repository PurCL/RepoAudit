# RepoAudit

RepoAudit is a repo-level bug detector for general bugs. Currently, it supports the detection of diverse bug types (such as Null Pointer Dereference, Memory Leak, and Use After Free) in multiple programming languages (including C/C++, Java, Python, and Go). It leverages [LLMSCAN](https://github.com/PurCL/LLMSCAN) to parse the codebase and uses LLM to mimic the process of manual code auditing. Compared with existing code auditing tools, RepoAudit offers the following advantages:

- Compilation-Free Analysis
- Multi-Lingual Support
- Multiple Bug Type Detection
- Customization Support

## Agents in RepoAudit

RepoAudit is a multi-agent framework for code auditing. We offer five agent instances in our current version:

- **MetaScanAgent** in `metascan.py`: Scan the project using tree-sitter–powered parsing-based analyzers and obtains the basic syntactic properties of the program.

- **DFBScanAgent** in `dfbscan.py`: Perform inter-procedural data-flow analysis as described in this [preprint](https://arxiv.org/abs/2501.18160). It detects data-flow bugs, including source-must-not-reach-sink bugs (e.g., Null Pointer Dereference) and source-must-reach-sink bugs (e.g., Memory Leak).

- **SliceScanAgent** in `slicescan.py`: An inter-procedural forward/backward slicing agent.

- **BugScanAgent** in `bugscan.py`: A general bug detector not restricted to data-flow bugs. Currently, it supports the detection of buffer overflow.

- **SampleScanAgent** in `samplescan.py`: An enhanced version of BugScanAgent that focuses on the most potentially buggy program locations. We attempt to detect bugs in [DARPA and ARPA-H's AIxCC Nginx Challenge Project](https://github.com/aixcc-public/challenge-004-nginx-source) using this agent.

For the detailed project structure, please refer to [ARCHITECTURE.md](ARCHITECTURE.md).

## Installation

1. Install the required dependencies:

   ```sh
   cd RepoAudit
   pip install -r requirements.txt
   ```

2. Ensure you have the Tree-sitter library and language bindings installed:

   ```sh
   cd lib
   python build.py
   ```

3. Configure the OpenAI API key. 

   ```sh
   export OPENAI_API_KEY=xxxxxx >> ~/.bashrc
   ```

   For Claude3.5, we use the model hosted by Amazon Bedrock. If you want to use Claude-3.5 and Claude-3.7, you may need to set up the environment first.


## Quick Start

1. We have prepare several benchmark programs in the directory `benchmark` for you to have a quick start. Several of them are sub-modules. You may need to clone them using the following commands:

   ```sh
   cd RepoAudit
   git submodule update --init --recursive
   ```

2. We offer the script `src/run_repoaudit.sh` that can scan the files in `benchmark/Java/toy/NPD` directory. You can execute the following commands:

   ```sh
   cd src
   sh run_repoaudit.sh dfbscan # Use the agent DFBScan
   sh run_repoaudit.sh bugscan # Use the agent BugScan
   ```
   
3. You can check the result json files and log files after finishing the scanning.


## Parallel Auditing Support

For some programs, a sequential analysis process may be quite time-consuming. To accelerate the analysis, you can choose parallel auditing. Specifically, you can set the option `--max-workers` to a larger value. By default, this option is set to 6 for parallel auditing.

## More

We currently open-source the implementation of [dfbscan](https://github.com/PurCL/RepoAudit). We will release more technical reports/research papers and open-source other agents in RepoAudit very soon. For more information, please refer to our website: [RepoAudit: Auditing Code As Human](https://repoaudit-home.github.io/).


## License

This project is licensed under the **GNU General Public License v2.0 (GPLv2)**.  You are free to use, modify, and distribute the software under the terms of this license, provided that derivative works are also distributed under the same license.

For full details, see the [LICENSE](LICENSE) file or visit the official license page: [https://www.gnu.org/licenses/old-licenses/gpl-2.0.html](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)