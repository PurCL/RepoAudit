# redis

Project Repo: https://github.com/redis/redis/tree/8fadebfcca0d514fd6949eaa72599ab5e163bd4c

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/redis/redis/tree/8fadebfcca0d514fd6949eaa72599ab5e163bd4c/src/redis-benchmark.c#L284

Bug traces:

* <    if (c) redisFree(c);, getRedisConfig>

Explanation:

* The pointer c is freed at line 46 and dereferenced at line 49 to access its connection_type field.


## Case 2

Is Reproduce: No

Program locations:

* https://github.com/redis/redis/tree/8fadebfcca0d514fd6949eaa72599ab5e163bd4c/deps/lua/src/strbuf.c#L113
* https://github.com/redis/redis/tree/8fadebfcca0d514fd6949eaa72599ab5e163bd4c/deps/lua/src/lua_cjson.c#L553
* https://github.com/redis/redis/tree/8fadebfcca0d514fd6949eaa72599ab5e163bd4c/deps/lua/src/lua_cjson.c#L680

Bug traces:

* <    free(s);, strbuf_free>
* <        strbuf_free(json);, json_check_encode_depth>
* <        json_check_encode_depth(l, cfg, current_depth, json);, json_append_data>

Explanation:

* The src object propagates to the caller function through pointer parameter `s`.
* The src object propagates to the caller function through the pointer parameter `json`.
* When lua_type(l, -1) is LUA_TTABLE, the freed pointer json from line 21 reaches the usage at line 22 where it's used as an argument to lua_array_length. This constitutes a use-after-free bug.


