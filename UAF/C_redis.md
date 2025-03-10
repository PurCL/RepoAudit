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


