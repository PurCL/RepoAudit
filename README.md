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

- **DebugScanAgent** in `debugscan.py`: A basic version of DebugScanAgent that targets the debugging task with a stack trace as its input. It can provide the explanation of the bug and provide a repair plan according to the user's request. Currently, it is still under the development.

## Installation

1. Create and activate a conda environment with Python 3.9.18:

   ```sh
   conda create -n repoaudit python=3.9.18
   conda activate repoaudit
   ```

2. Install the required dependencies:

   ```sh
   cd RepoAudit
   pip install -r requirements.txt
   ```

3. Ensure you have the Tree-sitter library and language bindings installed:

   ```sh
   cd lib
   python build.py
   ```

4. Configure the OpenAI API key. 

   ```sh
   export OPENAI_API_KEY=xxxxxx >> ~/.bashrc
   ```

   For Claude3.5, we use the model hosted by Amazon Bedrock. If you want to use Claude-3.5 and Claude-3.7, you may need to set up the environment first.


## Quick Start

1. We have prepared several benchmark programs in the `benchmark` directory for a quick start. Some of these are submodules, so you may need to initialize them using the following commands:

   ```sh
   cd RepoAudit
   git submodule update --init --recursive
   ```

2. We provide the script `src/run_repoaudit.sh` to scan files in the `benchmark/Java/toy/NPD` directory. You can run the following commands:

   ```sh
   cd src
   sh run_repoaudit.sh dfbscan # Use the agent DFBScan
   sh run_repoaudit.sh bugscan # Use the agent BugScan
   ```

3. After the scanning is complete, you can check the resulting JSON and log files.


## Parallel Auditing Support

For a large repository, a sequential analysis process may be quite time-consuming. To accelerate the analysis, you can choose parallel auditing. Specifically, you can set the option `--max-neural-workers` to a larger value. By default, this option is set to 6 for parallel auditing.
Also, we have set the parsing-based analysis in a parallel mode by default. The default maximal number of workers is 10.

## Website, Paper, and Docs

We currently open-source the implementation of [dfbscan](https://github.com/PurCL/RepoAudit). We will release more technical reports/research papers and open-source other agents in RepoAudit very soon. For more information, please refer to our website: [RepoAudit: Auditing Code As Human](https://repoaudit-home.github.io/).

If you want to know more details about the tool usage, project architecture, and extensions of RepoAudit, please refer to the following documents:

- [User Guide](docs/guide.md): Detailed instructions on installation, configuration, and usage of RepoAudit, particularly including the instructions on CLI and webUI usage.

- [Tool Architecture](docs/architecture.md): In-depth explanation of RepoAudit's multi-agent framework, including parsing-based analyzer/tools, LLM-driven tools, and the memory designs of the agents.

- [Extension](docs/extension.md): Guidelines for customizing RepoAudit for new bug types and supporting more programming languages.

## License

This project is licensed under the **GNU General Public License v2.0 (GPLv2)**.  You are free to use, modify, and distribute the software under the terms of this license, provided that derivative works are also distributed under the same license.

For full details, see the [LICENSE](LICENSE) file or visit the official license page: [https://www.gnu.org/licenses/old-licenses/gpl-2.0.html](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)