# Extending RepoAudit

## Adding New Bug Detectors

### 1. Create New Agent
```python
from repoaudit.agent import BaseAgent

class CustomBugAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.bug_patterns = []

    def analyze(self, code_unit):
        # Implement detection logic
        pass
```

### 2. Define Bug Patterns
- Create pattern definitions
- Implement detection rules
- Add test cases

### 3. Register Agent
```python
# In agents/__init__.py
from .custom_bug_agent import CustomBugAgent
REGISTERED_AGENTS['custom'] = CustomBugAgent
```

## Supporting New Languages

### 1. Tree-sitter Grammar
- Add language grammar files
- Build parser
- Test parsing capabilities

### 2. Language Handler
```python
# In languages/custom_lang.py
class CustomLanguageHandler:
    def parse_ast(self, code):
        # Implement parsing logic
        pass

    def extract_functions(self, ast):
        # Implement function extraction
        pass
```

### 3. Integration Steps
1. Add grammar to build.py
2. Create language-specific tests
3. Update configuration files
4. Add language-specific patterns

## Custom Analysis Rules

### 1. Rule Definition
```python
class CustomRule:
    def check(self, node):
        # Implement rule logic
        pass
```

### 2. Pattern Integration
- Add to pattern database
- Create test cases
- Document usage examples

### 3. LLM Prompts
- Design detection prompts
- Create validation prompts
- Add example cases
