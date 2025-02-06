from typing import Tuple

# Function to parse a bug report response
def parse_bug_report(response: str) -> Tuple[bool, bool]:
    # Check if the response indicates a bug
    is_buggy = "yes" in response.strip().lower()
    
    # Check if the response is ill-formed
    is_ill_formed = "yes" not in response.strip().lower() and "no" not in response.strip().lower()
    return is_buggy, is_ill_formed


# TODO: Define the response parsers for different forms of LLM responses