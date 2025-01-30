# coturn_server

Project Repo: https://github.com/coturn/coturn/tree/47008229cefaff6bfc4b231642d342f99712a5ad/src/server

## Case 1

Is Reproduce: No

Program locations:

* https://github.com/coturn/coturn/tree/47008229cefaff6bfc4b231642d342f99712a5ad/src/server/ns_turn_allocation.c#L453
* https://github.com/coturn/coturn/tree/47008229cefaff6bfc4b231642d342f99712a5ad/src/server/ns_turn_allocation.c#L326

Bug traces:

* <	ch_info *ret = NULL;, ch_map_get>
* <ch_map_get(&(a->chns), chnum, 1), allocation_get_new_ch_info>

Explanation:

* The NULL value of pointer `ret` at line 3 is returned to the caller at line 47 when `map` is NULL.
* The NULL value returned from ch_map_get at line 9 is dereferenced at line 11 without any NULL check.


## Case 2

Is Reproduce: Yes

Program locations:

* https://github.com/coturn/coturn/tree/47008229cefaff6bfc4b231642d342f99712a5ad/src/server/ns_turn_server.c#L1957

Bug traces:

* <	ts_ur_super_session *ss=NULL;, tcp_client_input_handler_rfc6062data>

Explanation:

* NULL value from line 10 can reach here without NULL check when `a` is NULL.


## Case 3

Is Reproduce: No

Program locations:

* https://github.com/coturn/coturn/tree/47008229cefaff6bfc4b231642d342f99712a5ad/src/server/ns_turn_maps.c#L623

Bug traces:

* <slh->extra_list = (addr_elem*)realloc(slh->extra_list, old_sz_mem + sizeof(addr_elem));, addr_list_add>

Explanation:

* `realloc` failure causes `slh->extra_list` to be NULL, leading to NPD during array access.


