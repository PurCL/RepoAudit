import re
from typing import List, Dict

def parse_paths(response: str) -> List[Dict]:
    """
    Parse the LLM response to extract all execution paths and their propagation details.
    
    Expected response format for each path:
    
      - Path <Path Number>: <Execution Path>.
          - Type: <type>; Name: <name>; Function: <function>; Index: <index>; Line: <line>; Dependency: <dependency>
          - (optionally, multiple propagation details per path)
    
    Returns:
        A list of dictionaries, one per path. Each dictionary has keys:
            - "path_number": str
            - "execution_path": str
            - "propagation_details": List[Dict] where each detail dict has keys:
                  "type", "name", "function", "index", "line", "dependency"
    """
    paths = []
    
    # Regex to match a path header line, e.g.,
    # "- Path 0: Single execution path through lines 1 → 2 → 3."
    path_header_re = re.compile(r"^- Path\s+(\d+):\s*(.+?)[\.;]$")
    
    # Regex to match a propagation detail line, e.g.,
    # "    - Type: Return; Name: null; Function: None; Index: 0; Line: 3; Dependency: SRC (null) is directly returned ... "
    detail_re = re.compile(
        r"^\s*-\s*Type:\s*([^;]+);\s*Name:\s*([^;]+);\s*Function:\s*([^;]+);\s*Index:\s*([^;]+);\s*Line:\s*([^;]+);\s*Dependency:\s*(.+)$"
    )
    
    current_path = None
    for line in response.splitlines():
        line = line.strip("\n")
        if not line.strip():
            continue
            
        # Check for path header
        header_match = path_header_re.match(line)
        if header_match:
            if current_path:
                paths.append(current_path)
            current_path = {
                "path_number": header_match.group(1).strip(),
                "execution_path": header_match.group(2).strip(),
                "propagation_details": []
            }
        else:
            # Check for propagation detail line (should be indented)
            detail_match = detail_re.match(line)
            if detail_match and current_path is not None:
                detail = {
                    "type": detail_match.group(1).strip(),
                    "name": detail_match.group(2).strip(),
                    "function": detail_match.group(3).strip(),
                    "index": detail_match.group(4).strip(),
                    "line": detail_match.group(5).strip(),
                    "dependency": detail_match.group(6).strip()
                }
                current_path["propagation_details"].append(detail)
    
    # Append last path if not yet added
    if current_path:
        paths.append(current_path)
    
    return paths

# Example usage:
if __name__ == "__main__":
    sample_response = """
- Path 0: Single execution path through lines 1 → 2 → 3.
    - Type: Return; Name: null; Function: None; Index: 0; Line: 3; Dependency: SRC (null) is directly returned from the function, propagating to the caller as the function's return value.
- Path 1: Another execution path through lines 4 → 5 → 6.
    - Type: Argument; Name: value; Function: updateValue; Index: 0; Line: 5; Dependency: SRC (value) is passed as an argument to updateValue.
    - Type: Return; Name: return value; Function: None; Index: 0; Line: 6; Dependency: SRC (value) is returned.
- Path 2: Another execution path through lines 4 → 5 → 6.
    "- No propagation; Dependency: Default return value -1 is unrelated to SRC."
"""
    parsed = parse_paths(sample_response)
    from pprint import pprint
    pprint(parsed)