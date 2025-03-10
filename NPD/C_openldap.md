# openldap

Project Repo: https://github.com/openldap/openldap/tree/519e0c94c9f3804813f691de487283ad7586f510

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/openldap/openldap/tree/519e0c94c9f3804813f691de487283ad7586f510/libraries/liblber/memory.c#L653
* https://github.com/openldap/openldap/tree/519e0c94c9f3804813f691de487283ad7586f510/libraries/libldap/fetch.c#L71
* https://github.com/openldap/openldap/tree/519e0c94c9f3804813f691de487283ad7586f510/libraries/libldap/url.c#L1616

Bug traces:

* <	return ber_strdup_x( s, NULL );, ber_strdup>
* <ber_strdup( urlstr ), ldif_open_url>
* <s, ldap_pvt_hex_unescape>

Explanation:

* The return value of ber_strdup_x containing NULL value is returned to the caller of function ber_strdup at line 4.
* The NULL value of pointer `p` from line 32 is passed as argument.
* The NULL value of parameter `s` at line 2 is dereferenced in the loop condition at line 11 without any NULL check.


## Case 2

Is Reproduce: No

Program locations:

* https://github.com/openldap/openldap/tree/519e0c94c9f3804813f691de487283ad7586f510/libraries/liblber/memory.c#L653
* https://github.com/openldap/openldap/tree/519e0c94c9f3804813f691de487283ad7586f510/libraries/libldap/fetch.c#L71

Bug traces:

* <\treturn ber_strdup_x( s, NULL );, ber_strdup>
* <ber_strdup( urlstr ), ldif_open_url>

Explanation:

* The return value of ber_strdup_x is returned to the caller of function ber_strdup.\nThe NULL value from ber_strdup at line 32 propagates to pointer `p`, then to pointer `s` through strchr at line 37, and is dereferenced at line 38 without NULL check.


