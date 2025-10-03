import os

from tree_sitter import Language, Parser
from pathlib import Path

cwd = Path(__file__).resolve().parent.absolute()

# clone tree-sitter if necessary
if not (cwd / "vendor/tree-sitter-c/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-c.git {cwd / "vendor/tree-sitter-c"}'
    )
    # Checkout to specific commit for language version 14 compatibility
    os.system(
        f'cd {cwd / "vendor/tree-sitter-c"} && git checkout cd44a2b1364d26d80daa208d3caf659a4c4e953d'
    )

if not (cwd / "vendor/tree-sitter-cpp/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-cpp.git {cwd / "vendor/tree-sitter-cpp"}'
    )
    # Checkout to specific commit for language version 14 compatibility
    os.system(
        f'cd {cwd / "vendor/tree-sitter-cpp"} && git checkout 12bd6f7e96080d2e70ec51d4068f2f66120dde35'
    )

if not (cwd / "vendor/tree-sitter-java/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-java.git {cwd / "vendor/tree-sitter-java"}'
    )
    # Checkout to specific commit for language version 14 compatibility
    os.system(
        f'cd {cwd / "vendor/tree-sitter-java"} && git checkout e10607b45ff745f5f876bfa3e94fbcc6b44bdc11'
    )

if not (cwd / "vendor/tree-sitter-python/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-python.git {cwd / "vendor/tree-sitter-python"}'
    )
    # Checkout to specific commit for language version 14 compatibility
    os.system(
        f'cd {cwd / "vendor/tree-sitter-python"} && git checkout 710796b8b877a970297106e5bbc8e2afa47f86ec'
    )

if not (cwd / "vendor/tree-sitter-go/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-go.git {cwd / "vendor/tree-sitter-go"}'
    )
    # Checkout to specific commit for language version 14 compatibility
    os.system(
        f'cd {cwd / "vendor/tree-sitter-go"} && git checkout 12fe553fdaaa7449f764bc876fd777704d4fb752'
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
