# libfreenect

Project Repo: https://github.com/OpenKinect/libfreenect/tree/d913755a25d09fbe2869a0d2acea78f589bfe6bf

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/OpenKinect/libfreenect/tree/d913755a25d09fbe2869a0d2acea78f589bfe6bf/wrappers/c_sync/libfreenect_sync.c#L220
* https://github.com/OpenKinect/libfreenect/tree/d913755a25d09fbe2869a0d2acea78f589bfe6bf/src/core.c#L133

Bug traces:

* <\tfreenect_init(&ctx, 0);, init_thread>
* <ctx, freenect_select_subdevices>

Explanation:

* The NULL value of pointer `ctx` at line 4 is passed as the first argument to the function freenect_select_subdevices at line 8.
* The NULL value of pointer `ctx` at line 1 is deferenced at line 3.


