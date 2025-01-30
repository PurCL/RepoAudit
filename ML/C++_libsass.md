# libsass

Project Repo: https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/permutate.hpp#L27

Bug traces:

* <    size_t* state = new size_t[L + 1];, permutate>

Explanation:

* The pointer `state` allocated at line 7 is not freed when the function returns early at line 12, causing a memory leak.


## Case 2

Is Reproduce: No

Program locations:

* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/permutate.hpp#L79

Bug traces:

* <    size_t* state = new size_t[L];, permutateAlt>

Explanation:

* The pointer `state` allocated at line 6 is not freed when the function returns early at line 11, causing a memory leak.


## Case 3

Is Reproduce: No

Program locations:

* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/sass.cpp#L39
* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/sass.cpp#L50
* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/sass_functions.cpp#L109
* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/context.cpp#L265

Bug traces:

* <    void* ptr = malloc(size);, sass_alloc_memory>
* <sass_alloc_memory(len), sass_copy_c_string>
* <sass_copy_c_string(imp_path), sass_make_import>
* <sass_make_import(
      inc.imp_path.c_str(),
      inc.abs_path.c_str(),
      res.contents,
      res.srcmap
    ), register_resource>

Explanation:

* The pointer `ptr` at line 3 is returned to the caller function at line 8.
* The pointer `cpy` at line 4 is returned to the caller function at line 6 through the return statement.
* The memory object returned by sass_copy_c_string at line 5 is assigned to v->imp_path at line 5, and the struct pointer v is returned to the caller at line 12.
* The pointer `import` created at line 28 is stored in import_stack at line 35, but the function throws an exception at line 58 before reaching the free site at line 71. This causes a memory leak.


## Case 4

Is Reproduce: No

Program locations:

* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/sass_context.cpp#L384
* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/sass_context.cpp#L244

Bug traces:

* <    Context* cpp_ctx = new Data_Context(*data_ctx);, sass_make_data_compiler>
* <c_ctx, sass_prepare_context>

Explanation:

* The pointer `cpp_ctx` at line 4 is passed as the second argument (index 1) to `sass_prepare_context` at line 5.\n`c_ctx` is not freed and not propagated to any function or caller after `calloc` fails at line 44.


## Case 5

Is Reproduce: No

Program locations:

* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/sass_context.cpp#L391
* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/sass_context.cpp#L244

Bug traces:

* <    Context* cpp_ctx = new File_Context(*file_ctx);, sass_make_file_compiler>
* <c_ctx, sass_prepare_context>

Explanation:

* `cpp_ctx` at line 4 is passed as the second argument to `sass_prepare_context` at line 5.\n`c_ctx` is not freed and not propagated to any function or caller after `calloc` fails at line 44.


## Case 6

Is Reproduce: No

Program locations:

* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/sass_functions.cpp#L107
* https://github.com/sass/libsass/tree/4da7c4bd13b8e9e5cd034f358dceda0bbba917d2/src/context.cpp#L265

Bug traces:

* <    Sass_Import* v = (Sass_Import*) calloc(1, sizeof(Sass_Import));, sass_make_import>
* <sass_make_import(\n      inc.imp_path.c_str(),\n      inc.abs_path.c_str(),\n      res.contents,\n      res.srcmap\n    ), register_resource>

Explanation:

* The pointer `v` allocated at line 3 is returned to the caller of `sass_make_import` at line 12.\nThe function throws an exception at line 58 before `import` is freed, resulting in a memory leak.


