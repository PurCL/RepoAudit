# How to Extend RepoAudit

RepoAudit is a customizable and multi-lingual code auditing framework. Currently, it supports the analysis of C, C++, Java, Python, and Go programs.
More bug detectors in these programming languages are under development.
If you want to customize RepoAudit for other bug types or programming languages, the following sections will help you.

## More Bug Types

RepoAudit mainly includes two different types of detectors: [`DFBScanAgent`](../src/agent/dfbscan.py) and [`BugScanAgent`](../src/agent/bugscan.py),
which target data-flow bug detection and general bug detection respectively.
Although the latter is more general, its performance heavily relies on reasoning models.
In contrast, reasoning models are not necessary for [`DFBScanAgent`](../src/agent/dfbscan.py).
To support more bug types, there are two different approaches:

### Supporting New Bug Types Using [`DFBScanAgent`](../src/agent/dfbscan.py)

If the bug type is an instance of a data-flow bug (i.e., detecting such bugs can be reduced to reachability analysis on a data-dependency graph),
you can follow the detection logic of inherent bug detectors built on [`DFBScanAgent`](../src/agent/dfbscan.py).
Here are the only two steps you need to take:

- Implement a sub-class of [`DFBScanExtractor`](../src/tstool/dfbscan_extractor/dfbscan_extractor.py) for the programming languages you target and place it in the corresponding directories named [`dfbscan_extractor`](../src/tstool/dfbscan_extractor/dfbscan_extractor.py). This extractor class offers the source/sink extractors for the detection. 

- Provide the prompt templates for intra-procedural data-flow analysis and path feasibility validation in the JSON files and place them in the corresponding sub-directories named [`dfbscan`](../src/prompt/Cpp/dfbscan/) in the directory [`prompt`](../src/prompt/).

You can refer to the implementations of existing sub-classes of [`DFBScanExtractor`](../src/tstool/dfbscan_extractor/dfbscan_extractor.py) and the prompt templates. Notably, if the data-flow facts propagate in the same form as Null Pointer Dereference, Memory Leak, and Use-After-Free, you can reuse inherent prompt templates in [`intra_dataflow_analyzer.json`](../src/prompt/Cpp/dfbscan/intra_dataflow_analyzer.json) and [`path_validator.json`](../src/prompt/Cpp/dfbscan/path_validator.json).

Lastly, when you run RepoAudit for scanning, you need to inform the auditor of which categories of the bug types are, i.e., whether it is a source-must-reach-sink bug or source-must-not-reach-sink bug, by determining whether specifying the option `--is-reachable` in the run command.

### Supporting New Bug Types Using [`BugScanAgent`](../src/agent/bugscan.py)

Similar to [`DFBScanAgent`](../src/agent/dfbscan.py), [`BugScanAgent`](../src/agent/bugscan.py) also requires the customization of a new extractor, which identifies the potential buggy points (such as the buffer access operations in the detection of buffer-overflow bugs) or the origins of faulty values (such as `NULL` values in the detection of Null Pointer Dereference bugs). Also, you need to provide a prompt template that demonstrates the detection logic. You can refer to the 
[`BOF_slice_bug_detector.json`](../src/prompt/Cpp/bugscan/BOF_slice_bug_detector.json) as an example, which targets the buffer-overflow bug detection.

Ideally, you only need to write prompt templates for detecting new types of bugs.
We will integrate more agents to support the synthesis of source/sink extractors.
More details can be found in the [paper](https://neurips.cc/virtual/2024/poster/95227).

## More Programming Languages

To support a new programming language, you need to follow the following steps:

- Add the repository link in the file [`lib/build.py`](../lib/build.py) and then execute `python lib/build.py` in the root directory for the installment.

- Follow existing parsing-based analyzers in the directory [`src/tstool`](../src/tstool), such as [`Cpp_TSAnalyzer`](../src/tstool/analyzer/Cpp_TS_analyzer.py) and [`Java_TSAnalzyer`](../src/tstool/analyzer/Cpp_TS_analyzer.py). Particularly, you need implement all the abstract methods in [`TSAnalyzer`](../src/tstool/).

- Implement the corresponding bug detectors for the new programming languages. Please refer the instructions above step by step.

- Modify the entry of RepoAudit, i.e., [`src/repoaudit.py`](../src/repoaudit.py), and append more choices of languages and bug types to enable the analysis.
