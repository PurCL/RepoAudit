# libsass

Project Repo: https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2

## Case 1

Program locations:

* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/permutate.hpp#L27

Bug traces:

* <    size_t* state = new size_t[L + 1];, permutate>

Explanation:

* The pointer `state` allocated at line 7 is not freed when the function returns early at line 12, causing a memory leak.


