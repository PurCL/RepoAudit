# RepoAudit

RepoAudit is a repo-level bug detector for general bugs. Currently, it supports the detection of diverse bug types (such as Null Pointer Dereference, Memory Leak, and Use After Free) in multiple programming languages (including C/C++, Java, Python, and Go). It leverages [LLMSCAN](https://github.com/PurCL/LLMSCAN) to parse the codebase and uses LLM to mimic the process of manual code auditing. Compared with existing code auditing tools, RepoAudit offers the following advantages:

- 🛡️ **Compilation-Free Analysis**
- 🌍 **Multi-Lingual Support**
- 🐞 **Multiple Bug Type Detection**
- ⚙️ **Customization Support**

## News 📰

**[June 2025]** The preprint of "An LLM Agent for Functional Bug Detection in Network Protocols" has been released, providing the technical details of `rfcscan`!

**[May 2025]** 🎉 Our paper "RepoAudit: Automated Code Auditing with Multi-Agent LLM Framework" has been accepted at ICML 2025! 🏆

**[March 2025]** RepoAudit has helped identify over 100 bugs in open-source projects this quarter!

## Agents in RepoAudit

RepoAudit is a multi-agent framework for code auditing. We offer two agent instances in our current version:

- **MetaScanAgent** in `metascan.py`: Scan the project using tree-sitter–powered parsing-based analyzers and obtains the basic syntactic properties of the program.

- **DFBScanAgent** in `dfbscan.py`: Perform inter-procedural data-flow analysis as described in this [preprint](https://arxiv.org/abs/2501.18160). It detects data-flow bugs, including source-must-not-reach-sink bugs (e.g., Null Pointer Dereference) and source-must-reach-sink bugs (e.g., Memory Leak).

We are keeping implementing more agents and will open-source them very soon. Utilizing DFBScanAgent and other agents, we have discovered hundred of confirmed and fixed bugs in open-source community. You can refer to this [bug list](https://repoaudit-home.github.io/bugreports.html).

## Installation

1. Create and activate a conda environment with Python 3.13:

   ```sh
   conda create -n repoaudit python=3.13
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

4. Configure the OpenAI API key and Anthropic API key:

   ```sh
   export OPENAI_API_KEY=xxxxxx >> ~/.bashrc
   export ANTHROPIC_API_KEY=xxxxxx >> ~/.bashrc
   ```

## Quick Start

Getting started with RepoAudit is simple — you can run a full scan on a project in just a few commands.

### Initialize the Benchmarks (one-time setup)

We provide several prepared benchmark programs in the `benchmark` directory. Some of these are Git submodules, so you may need to initialize them first:

```sh
cd RepoAudit
git submodule update --init --recursive
```

### Run a Scan with the Helper Script

We provide a ready-to-use script:
`src/run_repoaudit.sh`
This script scans a **target project folder** for specific types of bugs using our analysis engine.

You can run the script in several ways:

#### A. **Basic usage** (use default benchmark project and bug type):

```sh
cd src
sh run_repoaudit.sh
```

This will scan the default toy project located at:

```
../benchmark/Python/toy
```

for **NPD** bugs (Null Pointer Dereference).

#### B. **Specify your own project path**:

```sh
sh run_repoaudit.sh /path/to/your/project
```

This will scan the provided project for **NPD** bugs by default.

You can use either a **relative** or **absolute** path.

#### C. **Specify bug type too**:

```sh
sh run_repoaudit.sh /path/to/your/project UAF
```

The second argument lets you choose the **bug type** to scan for. Supported types are:

| Code | Meaning                  |
| ---- | ------------------------ |
| MLK  | Memory Leak              |
| NPD  | Null Pointer Dereference |
| UAF  | Use After Free           |

> ⚠️ Bug type is **case-insensitive** (`npd`, `NPD`, or `NpD` all work).


### View Results

Once the scan finishes, the tool generates **JSON** and **log** files containing the findings.
You can find these files in the output directory printed by the script.

✅ **That's it!**

With just one script, you can quickly run RepoAudit on either a built-in benchmark project or any project path you specify.



## Parallel Auditing Support

For a large repository, a sequential analysis process may be quite time-consuming. To accelerate the analysis, you can choose parallel auditing. Specifically, you can set the option `--max-neural-workers` to a larger value. By default, this option is set to 30 for parallel auditing.
Also, we have set the parsing-based analysis in a parallel mode by default, which is determined by the option `--max-symbolic-workers`. The default maximal number of workers is 30.

## Website, Documentation and Papers

We have open-sourced the implementation of [dfbscan](https://github.com/PurCL/RepoAudit). Other agents in RepoAudit will be released soon. For more information, please visit our website: [RepoAudit: Auditing Code As Human](https://repoaudit-home.github.io/).

For more details about tool usage, project architecture, and extensions of RepoAudit, please refer to the following documents:

- [User Guide](https://github.com/PurCL/RepoAudit/wiki/01.-User-Guide): Detailed instructions on installation, configuration, and usage of RepoAudit, including CLI and webUI usage.

- [Project Architecture](https://github.com/PurCL/RepoAudit/wiki/02.-Project-Architecture): In-depth explanation of RepoAudit's multi-agent framework, including parsing-based analyzers/tools, LLM-driven tools, and agent memory designs.

- [Extension](https://github.com/PurCL/RepoAudit/wiki/03.-How-to-Extend): Guidelines for customizing RepoAudit to support new bug types and programming languages.

- [DeepWiki](https://deepwiki.com/PurCL/RepoAudit): All-in-one documentation generated by [`Devin`](https://devin.ai/).


If you find our research or tools helpful, please cite the following papers. More technical reports/research papers will be released in the future.

```bibtex
@inproceedings{repoaudit2025,
  title={RepoAudit: An Autonomous LLM-Agent for Repository-Level Code Auditing},
  author={Guo, Jinyao* and Wang, Chengpeng* and Xu, Xiangzhe and Su, Zian and Zhang, Xiangyu},
  booktitle={Proceedings of the 42nd International Conference on Machine Learning},
  year={2025},
  note={*Equal contribution}
}

@article{rfcscan2025,
  title={An LLM Agent for Functional Bug Detection in Network Protocols},
  author={Zheng, Mingwei and Wang, Chengpeng and Liu, Xuwei and Guo, Jinyao and Feng, Shiwei and Zhang, Xiangyu},
  journal={arXiv preprint arXiv:2506.00714},
  year={2025}
}
```

## License

This project is licensed under [Purdue license](LICENSE).

## Contact

For any questions or suggestions, please submit issues or pull requests on GitHub. You can also reach out to our maintainers:

- Chengpeng Wang (Purdue University) - [wang6590@purdue.edu](mailto:wang6590@purdue.edu)

- Jinyao Guo (Purdue University) - [guo846@purdue.edu](mailto:guo846@purdue.edu) 

- Zhuo Zhang (Columbia University) - [zz3474@columbia.edu](mailto:zz3474@columbia.edu)
