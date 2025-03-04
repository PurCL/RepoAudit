import os

from tree_sitter import Language, Parser
from pathlib import Path

cwd = Path(__file__).resolve().parent.absolute()

# clone tree-sitter if necessary
if not (cwd / "vendor/tree-sitter-c/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-c.git {cwd / "vendor/tree-sitter-c"}'
    )

if not (cwd / "vendor/tree-sitter-cpp/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-cpp.git {cwd / "vendor/tree-sitter-cpp"}'
    )

if not (cwd / "vendor/tree-sitter-java/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-java.git {cwd / "vendor/tree-sitter-java"}'
    )

if not (cwd / "vendor/tree-sitter-python/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-python.git {cwd / "vendor/tree-sitter-python"}'
    )

if not (cwd / "vendor/tree-sitter-go/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-go.git {cwd / "vendor/tree-sitter-go"}'
    )

Language.build_library(
    # Store the library in the `build` directory
    str(cwd / "build/my-languages.so"),
    
    # Include one or more languages
    [
        str(cwd / "vendor/tree-sitter-c"),
        str(cwd / "vendor/tree-sitter-cpp"),
        str(cwd / "vendor/tree-sitter-java"), 
        str(cwd / "vendor/tree-sitter-python"), 
        str(cwd / "vendor/tree-sitter-go"), 
    ],
)
