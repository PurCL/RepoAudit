# i18n

Project Repo: https://github.com/unicode-org/icu/tree/maint/maint-54/icu4c/source/i18n

## Case 1

Is Reproduce: Yes

Program locations:

* https://github.com/unicode-org/icu/tree/maint/maint-54/icu4c/source/i18n/zonemeta.cpp#L111
* https://github.com/unicode-org/icu/tree/maint/maint-54/icu4c/source/i18n/zonemeta.cpp#L684

Bug traces:

* <    uprv_free(entry);, deleteOlsonToMetaMappingEntry>
* <entry, createMetazoneMappings>

Explanation:

* The src object propagates to the caller function through the void pointer parameter `obj`, which points to the same memory object as the freed pointer `entry`.
* The entry object is freed at line 68 by deleteOlsonToMetaMappingEntry and then freed again at line 69 by uprv_free.


## Case 2

Is Reproduce: No

Program locations:

* https://github.com/unicode-org/icu/tree/maint/maint-54/icu4c/source/i18n/zonemeta.cpp#L685

Bug traces:

* <                        uprv_free(entry);, createMetazoneMappings>

Explanation:

* The pointer entry is freed twice - first by deleteOlsonToMetaMappingEntry at line 68, then by uprv_free at line 69, causing a double-free vulnerability.


## Case 3

Is Reproduce: No

Program locations:

* https://github.com/unicode-org/icu/tree/maint/maint-54/icu4c/source/i18n/tznames_impl.cpp#L1557

Bug traces:

* <                uprv_free(p);, createInstance>

Explanation:

* The alias `regions` (same memory block as `p`) is freed again after being partially freed at line 84, causing a double-free UAF.


