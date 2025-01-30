# net_4cd8371

Project Repo: https://github.com/torvalds/linux/tree/4cd8371a234d051f9c9557fcbb1f8c523b1c0d10/drivers/net

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/torvalds/linux/tree/4cd8371a234d051f9c9557fcbb1f8c523b1c0d10/drivers/net/ethernet/netronome/nfp/nfpcore/nfp_cppcore.c#L800

Bug traces:

* <	area = nfp_cpp_area_alloc(cpp, NFP_CPP_ID(7, NFP_CPP_ACTION_RW, 0),, nfp_cpp_area_cache_add>

Explanation:

* The pointer `area` at line 9 is not freed and not propagated to any function before the function returns at line 16. Thus there is a memory leak bug.


