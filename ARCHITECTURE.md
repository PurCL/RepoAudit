# Architecture

The project structure is as follows:

```
# In src directory
├── agent                # Directory containing different agents for different uses
|   ├── agent.py         # The base class of agent
│   ├── bugscan.py       # The agent for general bug detection
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
│   ├── dfbscan          # LLM tools used in dfbscan
│   │   ├── intra_dataflow_analyzer.py  # LLM tool: Collect intra-procedural data-flow facts
│   │   └── path_validator.py   # LLM tool: Validate the path reachability
│   ├── samplescan       # LLM tools used in samplescan
│   │   ├── function_bug_detector.py   # LLM tool: Detect bugs in single functions
│   │   └── seed_selector.py # LLM tool: Select potential buggy locations
│   └── slicescan        # LLM tools used in slicescan
│       └── intra_slicer.py  # LLM tool: Intra-procedural program slicing
├── memory
│   ├── report           # Bug report 
│   │   └── bug_report.py
│   ├── semantic         # Semantic properties focused in different agents
│   │   ├── bugscan_state.py
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