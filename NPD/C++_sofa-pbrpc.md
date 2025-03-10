# sofa-pbrpc

Project Repo: https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b

## Case 1

Program locations:

* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/pbjson.cc#L242
* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/pbjson.cc#L523
* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/pbjson.cc#L512

Bug traces:

* <        return NULL;, parse_msg>
* <parse_msg(msg, allocator), pb2json>
* <json, json2string>

Explanation:

* The NULL value is directly returned to the caller of parse_msg function at line 5.
* The return value from parse_msg at line 4 propagates to pointer `json` which is passed as the first argument to json2string at line 5.
* The pointer `json` from line 1 is deferenced without NULL check.


