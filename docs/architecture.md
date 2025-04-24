# Project Architecture

## Overview

RepoAudit is a multi-agent framework. Each [`agent`](../src/agent/) targets a specific code auditing task, such as data-flow bug detection, program slicing, and general bug detection. An agent can utilize parsing-based analyzers (e.g., the interfaces of [`src/tstool/analyzer/TS_analyzer.py`](../src/tstool/analyzer/TS_analyzer.py)), LLM-driven analyzers (e.g., different LLM-based tools in [`src/llmtool`](../src/llmtool/)), and even [`agents`](../src/agent/).

When scanning a repository, we first initialize a parsing-based analyzer (i.e., an instance of [`TSAnalyzer`](../src/tstool/analyzer/TS_analyzer.py)) for code indexing and then invoke a specific agent for scanning. The results of the parsing-based analyzer, agent, and final results (such as bug reports) are maintained in the memory of RepoAudit.

Here is a pipeline of RepoAudit

```

                         +-------------+     +---------+      
                         |    TSTool   |     | LLMTool |
                         +-------------+     +---------+
                            ↑        ↓            ↓
            +----------------+     +-------------------+     +------------------+
Code   →    |   TSAnalyzer   |  →  |      Agents       |  →  |      Reports     |
            | (AST Parsing)  |     |(Semantic Analysis)|     |  (Final Results) |
            +----------------+     +-------------------+     +------------------+
                    ↓                     ↑    ↓                       ↓
        +--------------------------------------------------------------------------+  
        |   [Syntactic Memory]       [Semantic Memory]         [Report Memory]     |
Memory  |     Syntactic Info        Semantic Properties          Scan Report       |
        |  (Value/Function/API)        (Agent State)          (Bug/Debug results)  |
        +--------------------------------------------------------------------------+
```

In what follows, we offer more illustrations on these core componets.
If you want to have an overview of our project structure, you can refer to the file [structure.md](structure.md).


## Core Components

### TSAnalyzer: Parsing-based Analysis

RepoAudit leverages [`tree-sitter`](https://tree-sitter.github.io/tree-sitter/) to derive the abstract syntax tree (AST) of the repository code.
Specifically, it extracts the basic constructs of each function, including critical values (e.g., parameters, arguments, output values, and return values), branches (e.g., if-statements), and loops (e.g., for-loops and while-loops). 
Based on the derived constructs, it further constructs a call graph (based on function names and parameter/argument numbers), control-flow order analysis, and CFL-reachability analysis.
Notably, such parsing-based analysis may approximate the semantic properties, especially caller-callee relationships, though it may not be sound or complete in cases involving class hierarchy and function pointers.

The above functionalities are supported by different sub-classes of [`TSAnalyzer`](../src/tstool/analyzer/TS_analyzer.py), targeting different programming languages.
The source code is located in the directory [`src/tstool/analyzer`](../src/tstool/analyzer/).

### Agent

An agent is a component targeting a specific code auditing task, such as program slicing, debugging, bug detection, program repair. Currently, RepoAudit only targets the bug detection task, while it can be easily extended to support other tasks. Notably, as a multi-agent framework, an agent in RepoAudit can leverage the results of other agents. In the file [`src/agent/agent.py`](../src/agent/agent.py), we offer the definition of the base class [`Agent`](../src/agent/agent.py), which have the following several sub-classes focusing on concrete tasks:

#### MetaScanAgent

[MetaScanAgent](../src/agent/metascan.py) is a simple agent for demo. It wraps the parsing-based analyzer without additional symbolic or neural analysis.

#### DFBScanAgent

[DFBScanAgent](../src/agent/dfbscan.py) is our current open-sourced agent for data-flow bug detection. It implements the analysis workflow presented in this [paper](https://arxiv.org/abs/2501.18160). Our implemented version can support the detection of the following bug types in different programming languages.

| Bug Type                    | C   | C++ | Java | Python | Go  |
|-----------------------------|-----|-----|------|--------|-----|
| Null Pointer Dereference    | ✓   | ✓   | ✓    | ✓      | ✓   |
| Memory Leak                 | ✓   | ✓   |      |        |     |
| Use After Free              | ✓   | ✓   |      |        |     |

For more programming languages and bug types, we will offer detailed instructions on how to extend the agent in the [extensions.md](extensions.md).

#### SliceScanAgent

[SliceScanAgent](../src/agent/slicescan.py) is an agent that performs an inter-procedural forward/backward slicing.
Given a seed or mutliple seeds in the same program location, the agent can derive a list of slices across the function boundaries at most `call-depth` times.

#### BugScanAgent

[BugScanAgent](../src/agent/bugscan.py) is an agent that targets more general bug detection than [DFBScanAgent](../src/agent/dfbscan.py). 
As a prototype, we have customized a buffer-overflow detector built upon this agent, which can not be supported by [DFBScanAgent](../src/agent/dfbscan.py). 
The agent invokes a series of instances of [SliceScanAgent](../src/agent/slicescan.py) to retrieve the contexts of the potential buggy operations for further checking.
Currently, we have customized the following several detectors for different bug types in these programming languages.

| Bug Type                    | C   | C++ | Java | Python | Go  |
|-----------------------------|-----|-----|------|--------|-----|
| Null Pointer Dereference    | ✓   | ✓   | ✓    | ✓      | ✓   |
| Memory Leak                 | ✓   | ✓   |      |        |     |
| Use After Free              | ✓   | ✓   |      |        |     |
| Buffer Overflow             | ✓   | ✓   |      |        | ✓   |

For more programming languages and bug types, we will offer detailed instructions on how to extend the agent in the [extensions.md](extensions.md).

#### SampleScanAgent

[SampleScanAgent](../src/agent/samplescan.py) is a variant of [BugScanAgent](../src/agent/bugscan.py). 
As the number of potential buggy operations can be very large,
we first leverage an LLM-driven tool to filter out safe usage based on single-function context and then follow the workflow of [BugScanAgent](../src/agent/bugscan.py).
Our current implementation is released to DARPA for reproducing bugs in DARPA and ARPA-H's AIxCC Nginx Challenge Project.
However, selecting potential buggy operations in BugScanAgent requires further exploration in the future.

#### DebugScanAgent

[DebugScanAgent](../src/agent/debugscan.py) is a debugging agent.
Similar to [BugScanAgent](../src/agent/bugscan.py) and [SampleScanAgent](../src/agent/samplescan.py),
[DebugScanAgent](../src/agent/debugscan.py) derives the debugging context according to a given stack trace
and generates an explanation or repair plan.
Currently, this agent is a very early-staged version for Java program debugging only and requires further developmenet.


### TSTool: Parsing-based Tools

To support a specific agent, we currently offer several additional parsing-based tools for different bug types in different programming languages. For example, in the detection of Null Pointer Dereference (NPD) in C++ programs, we need to identify the source values (i.e., potential NULL values).
Utilizing the interfaces offered by [`TSAnalyzer`](../src/tstool/analyzer/TS_analyzer.py)), we create [`Cpp_NPD_Extractor`](../src/tstool/dfbscan_extractor/Cpp/Cpp_NPD_Extractor.py) for the extraction of NULL values.

You can also follow the definition of [`Cpp_NPD_Extractor`](../src/tstool/dfbscan_extractor/Cpp/Cpp_NPD_Extractor.py) when you define your own agent and the relevant parsing-based tools.
We will also integrate a synthesis agent into RepoAudit to synthesize specific parsing-based tools, such as source extractors, by following the design in our previous work [LLMDFA](https://neurips.cc/virtual/2024/poster/95227).

### LLMTool: LLM-driven Tools

LLM-driven tools enable semantic analysis of source code without compilation.
Similar to traditional IR-based program analyzers,
these tools derive program facts or transform source code for further analysis, functioning similarly to LLVM passes in LLVM-based C/C++ analyzers.

As shown in the file [`src/llmtool/LLM_tool.py`](../src/llmtool/LLM_tool.py) containing the base class [`LLMTool`](../src/llmtool/LLM_tool.py),
an instance of a LLM-driven tool recieves and returns a specific form of input and output objects, respectively.
When defining a LLM-driven tool, i.e., the sub-class of `LLMTool`, we also need to define the sub-classes of `LLMToolInput` and `LLMToolOutput`.
Also, we have to provide the corresponding prompting template in the directory [`src/prompt`](../src/prompt/).

Consider the LLM-driven tools used by [DFBScanAgent](../src/agent/dfbscan.py).
We include two LLM-driven tools in the directory [src/llmtool/dfbscan](../src/llmtool/dfbscan/).

- [IntraDataFlowAnalyzer](../src/llmtool/dfbscan/intra_dataflow_analyzer.py) derives the data-flow facts along different program paths in single functions. It corresponds to `explorer` in the [paper](https://arxiv.org/abs/2501.18160).

- [PathValidator](../src/llmtool/dfbscan/path_validator.py) validates the feasiblity of a program path. It corresponds to `validator` in the [paper](https://arxiv.org/abs/2501.18160).


### Memory

As a multi-agent framework for code auditing, RepoAudit contains three kinds of memory, which are implemented in the directory [`src/memory/`](../src/memory/).

### Syntactic Memory

Syntactic memory maintains critical constructs for code auditing. RepoAudit mainly focuses on the program values in different functions.
Utilizing [`TSAnalyzer`](../src/tstool/analyzer/TS_analyzer.py), it stores the [Function](../src/memory/syntactic/function.py), [API](../src/memory/syntactic/api.py), and [Value](../src/memory/syntactic/value.py) info in the syntactic memory.
These three constructs are then retrieved by agents when the agents invoke the LLM-driven tools.

In the future, we may need to extend the syntactic memory and maintain more expressive compilation-independent IR constructs.

### Semantic Memory

Semantic memory maintains the intermediate states of agents. 
For each agent, we define a corresponding state as the sub-class of [State](../src/memory/semantic/state.py).
For example, [DFBScanState](../src/memory/semantic/dfbscan_state.py) stores the data-flow facts along different paths and also the relevant parameters/return values/arguments/output values.
Based on the semantic memory, the agents can finally compute the outputs and obtain the reports of the agents.

### Report

Reports maintain the final results of the agents.
Currently, there are two types of reports: bug reports and debug reports, 
which are the outputs of the end-user agents including [`DFBScanAgent`](../src/agent/dfbscan.py), [`BugScanAgent`](../src/agent/bugscan.py), [`SampleScanAgent`](../src/agent/samplescan.py), and [`DebugScanAgent`](../src/agent/debugscan.py).
For [`MetaScanAgent`](../src/agent/metascan.py) and [`SliceScanAgent`](../src/agent/slicescan.py), since they do not compute additional program facts or end-user results,
we do not explicitly define their specific report formats.

## Project Structure

For your reference, we append the project structure as follows:

```
# In src directory
├── agent                # Directory containing different agents for different uses
│   ├── agent.py         # The base class of agent
│   ├── bugscan.py       # The agent for general bug detection
│   ├── debugscan.py     # The agent for stack trace-based debugging
│   ├── dfbscan.py       # The agent for data-flow bug detection. Implemented in RepoAudit.
│   ├── samplescan.py    # The agent for selective bug detection. Enhanced version of bugscan.
│   ├── slicescan.py     # The agent for inter-procedural slicing.
│   └── metascan.py      # The agent for syntactic analysis
├── llmtool              # Directory for LLM-based analyzers
│   ├── LLM_tool.py      # The base class of LLM-based analyzers as tools
│   ├── LLM_utils.py     # Utility class that invokes different LLMs
│   ├── bugscan          # LLM tools used in bugscan
│   │   ├── slice_bug_detector.py  # LLM tool: Detect bugs in slices
│   │   └── slice_inliner.py  # LLM tool: Inline multiple slices into a single function
│   ├── debugscan        # LLM tools used in debugscan
│   │   ├── debug_request_formulator.py   # LLM tool: Formulate the user's debugging request
│   │   └── debug_slice_analyzer.py       # LLM tool: Analyze slices for debugging
│   ├── dfbscan          # LLM tools used in dfbscan
│   │   ├── intra_dataflow_analyzer.py  # LLM tool: Collect intra-procedural data-flow facts
│   │   └── path_validator.py   # LLM tool: Validate the path reachability
│   ├── samplescan       # LLM tools used in samplescan
│   │   ├── function_bug_detector.py   # LLM tool: Detect bugs in single functions
│   │   └── seed_selector.py # LLM tool: Select potential buggy locations
│   ├── slicescan        # LLM tools used in slicescan
│   │   ├── intra_slicer.py  # LLM tool: Intra-procedural program slicing
│   └── utility                          # Utility LLM tools
│       └── audit_request_formulator.py  # LLM tool: Formulate user's request for bugscan, dfbscan, etc.
├── memory
│   ├── report           # Reports of agents 
│   │   ├── debug_report.py 
│   │   └── bug_report.py
│   ├── semantic         # Semantic properties focused in different agents
│   │   ├── bugscan_state.py
│   │   ├── debugscan_state.py
│   │   ├── dfb_state.py
│   │   ├── metascan_state.py
│   │   ├── samplescan_state.py
│   │   ├── slicescan_state.py
│   │   └── state.py
│   └── syntactic        # Syntactic properties, i.e., AST info
│       ├── api.py
│       ├── function.py
│       └── value.py
├── tstool
│   ├── analyzer         # parsing-based analyzer
│   │   ├── Cpp_TS_analyzer.py      # C/C++ analyzer
│   │   ├── Go_TS_analyzer.py       # Go analyzer
│   │   ├── Java_TS_analyzer.py     # Java analyzer
│   │   ├── Python_TS_analyzer.py   # Python analyzer
│   │   ├── TS_analyzer.py          # Base class
│   ├── bugscan_extractor # Extractors used in bugscan (based on parsing)
│   │   ├── Cpp
│   │   │   ├── Cpp_BOF_extractor.py
│   │   │   ├── Cpp_MLK_extractor.py
│   │   │   ├── Cpp_NPD_extractor.py
│   │   │   ├── Cpp_UAF_extractor.py
│   │   ├── Go
│   │   │   ├── Go_BOF_extractor.py
│   │   │   ├── Go_NPD_extractor.py
│   │   ├── Java
│   │   │   └── Java_NPD_extractor.py
│   │   ├── Python
│   │   │   └── Python_NPD_extractor.py
│   │   └── bugscan_extractor.py
│   └── dfbscan_extractor # Extractors used in dfbscan (based on parsing)
│       ├── Cpp
│       │   ├── Cpp_MLK_extractor.py
│       │   ├── Cpp_NPD_extractor.py
│       │   ├── Cpp_UAF_extractor.py
│       ├── Java
│       │   └── Java_NPD_extractor.py
│       └── dfbscan_extractor.py
├── prompt # Prompt templates
│   ├── Cpp
│   │   ├── bugscan    # Prompts used in bugscan for Cpp program analysis
│   │   │   ├── BOF_slice_bug_detector.json
│   │   │   ├── MLK_slice_bug_detector.json
│   │   │   ├── NPD_slice_bug_detector.json
│   │   │   ├── UAF_slice_bug_detector.json
│   │   │   └── slice_inliner.json
│   │   ├── dfbscan    # Prompts used in dfbscan for Cpp program analysis
│   │   │   ├── intra_dataflow_analyzer.json
│   │   │   └── path_validator.json
│   │   ├── samplescan # Prompts used in samplescan for Cpp program analysis
│   │   │   ├── BOF_seed_selector.json
│   │   │   ├── NPD_seed_selector.json
│   │   │   ├── UAF_seed_selector.json
│   │   │   └── function_bug_detector.json
│   │   └── slicescan  # Prompts used in slicescan for Cpp program analysis
│   │       ├── backward_slicer.json
│   │       └── forward_slicer.json
│   ├── Go
│   │   ├── bugscan    # Prompts used in bugscan for Go program analysis
│   │   │   ├── BOF_slice_bug_detector.json
│   │   │   ├── NPD_slice_bug_detector.json
│   │   │   └── slice_inliner.json
│   │   ├── dfbscan    # Prompts used in dfbscan for Go program analysis
│   │   ├── samplescan # Prompts used in samplescan for Go program analysis
│   │   └── slicescan  # Prompts used in slicescan for Go program analysis
│   │       ├── backward_slicer.json
│   │       └── forward_slicer.json
│   ├── Java
│   │   ├── bugscan    # Prompts used in bugscan for Java program analysis
│   │   │   ├── NPD_slice_bug_detector.json
│   │   │   └── slice_inliner.json
│   │   ├── debugscan  # Prompts used in debugscan for Java stack trace-based debugging
│   │   │   ├── debug_request_formulator.json
│   │   │   └── debug_slice_analyzer.json
│   │   ├── dfbscan    # Prompts used in dfbscan for Java program analysis
│   │   │   ├── intra_dataflow_analyzer.json
│   │   │   └── path_validator.json
│   │   ├── samplescan # Prompts used in samplescan for Java program analysis
│   │   └── slicescan  # Prompts used in slicescan for Java program analysis
│   │       ├── backward_slicer.json
│   │       └── forward_slicer.json
│   └── Python
│       ├── bugscan    # Prompts used in bugscan for Python program analysis
│       │   ├── NPD_slice_bug_detector.json
│       │   └── slice_inliner.json
│       ├── dfbscan    # Prompts used in dfbscan for Python program analysis
│       ├── samplescan # Prompts used in samplescan for Python program analysis
│       └── slicescan  # Prompts used in slicescan for Python program analysis
│           ├── backward_slicer.json
│           └── forward_slicer.json
└── ui                   # UI classes
│   ├── logger.py        # Logger class
│   └── web_ui.py        # Web UI class (under construction)
├── repoaudit.py         # Main entry of RepoAudit
├── run_repoaudit.sh     # Script for analyzing one project
├── run_repoaudit_all.sh # Script for analyzing multiple projects
```