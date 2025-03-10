# memcached

Project Repo: https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996

## Case 1

Program locations:

* https://github.com/memcached/memcached/tree/e15e1d6b967eed53ddcfd61c0c90c38d0b017996/memcached.c#L4629

Bug traces:

* <        char *list = strdup(settings.inter);, server_sockets>

Explanation:

* The pointer `list` at line 9 is not freed before the function returns at line 27 when encountering invalid IPv6 address.


