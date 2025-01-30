# wabt_tools

Project Repo: https://github.com/WebAssembly/wabt/tree/b2194657c4b9b90599ae02b36a02a10dbedc32c4/src/tools

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/WebAssembly/wabt/tree/b2194657c4b9b90599ae02b36a02a10dbedc32c4/src/tools/wasm-opcodecnt.cc#L227

Bug traces:

* <    delete[] data;, ProgramMain>

Explanation:

* The freed pointer data is freed again at line 47.


