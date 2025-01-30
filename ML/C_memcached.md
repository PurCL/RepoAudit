# memcached

Project Repo: https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996

## Case 1

Is Reproduce: No

Program locations:

* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/memcached.c#L5416

Bug traces:

* <            subopts_orig = subopts = strdup(optarg); /* getsubopt() changes the original args */, main>

Explanation:

* The pointer `subopts_orig` at line 310 is not freed before the function returns at line 321.


## Case 2

Is Reproduce: Yes

Program locations:

* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/memcached.c#L4629

Bug traces:

* <        char *list = strdup(settings.inter);, server_sockets>

Explanation:

* The pointer `list` at line 9 is not freed before the function returns at line 27 when encountering invalid IPv6 address.


## Case 3

Is Reproduce: No

Program locations:

* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/memcached.c#L5733

Bug traces:

* <            temp_portnumber_filename = malloc(len);, main>

Explanation:

* The pointer `temp_portnumber_filename` at line 627 is not freed and not propagated to any function when `portnumber_file == NULL`.


## Case 4

Is Reproduce: No

Program locations:

* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/memcached.c#L399
* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/thread.c#L400

Bug traces:

* <        c->msglist = (struct msghdr *)malloc(sizeof(struct msghdr) * c->msgsize);, conn_new>
* <conn_new(item->sfd, item->init_state, item->event_flags,\n                           item->read_buffer_size, item->transport, me->base), thread_libevent_process>

Explanation:

* `c` (containing `msglist`) is returned to the caller.\nThe memory allocated for 'c' at line 15 is not freed and not propagated to other functions, resulting in a memory leak.


## Case 5

Is Reproduce: No

Program locations:

* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/cache.c#L22
* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/testapp.c#L153

Bug traces:

* <    cache_t* ret = calloc(1, sizeof(cache_t));, cache_create>
* <cache_create(\"test\", sizeof(uint32_t), sizeof(char*),\n                                  NULL, NULL), cache_redzone_test>

Explanation:

* The pointer `ret` at line 4 is returned to the caller of `cache_create` at line 27.\nThe assert at line 18 fails, causing program termination. The pointer `cache` at line 4 is not freed, resulting in a memory leak.


## Case 6

Is Reproduce: No

Program locations:

* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/cache.c#L79
* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/cache.c#L48
* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/cache.c#L77
* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/testapp.c#L75

Bug traces:

* <        object = ret = malloc(cache->bufsize);, cache_alloc>
* <ptr, get_object>
* <get_object(ret), cache_alloc>
* <cache_alloc(cache), cache_fail_constructor_test>

Explanation:

* `ret` (src) is passed to `get_object` at line 11.\nThe pointer `ptr` at line 1 is propagated to the caller via `return pre + 1` (line 4).  \n`object` (derived from `ret`) is returned to the caller.  \nThe pointer `ptr` at line 8 is not freed and not propagated to any function, causing a memory leak.


