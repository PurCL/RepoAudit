# Development Plan


## Open-Source Preparation

### Detection Agent

- BugScan (DONE)

- DFAScan (ICML submission version, TODO) (Jinyao & Chengpeng)

### UI 

- DFAScan

  - Data-flow spec customization (source/sink): Interaction with LLMs  (Chengpeng)

  - Analysis UI

    - Terminal UI (Chengpeng)

    - Web UI (Jinyao)


### Analyze

- Global variables and class member values

- Different data-flow propagation rules

- Refactor the format of external values in slicing (o3-mini can not produce them in the given format)

- Refactor the output/ret, para/arg conversion


### Doc

- Quick Start

- Project Architecture

- Add New Bug Detectors

- Support New Languages


## Maintenance

### Testing

- Benchmark construction (e.g., small toy programs in five languages)

- Regression testing


### Prompt

- Prompt synthesis

- Modular design


## Research

### Multi-Modal Support

- Specification Inference Agent

  - PatInf: Infer SFA from code (Jiasheng)

  - DocInfer: Infer protocol spec from doc (Mingwei)

### Functional Bug Detection

- Java: Defect4j benchmark

- Performance bug detection
