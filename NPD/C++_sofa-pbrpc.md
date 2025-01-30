# sofa-pbrpc

Project Repo: https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b

## Case 1

Is Reproduce: No

Program locations:

* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/pbjson.cc#L61
* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/pbjson.cc#L269

Bug traces:

* <    rapidjson::Value* json = NULL;, field2json>
* <field2json(msg, field, allocator), parse_msg>

Explanation:

* The NULL value of json at line 12 is returned to the caller at line 186.
* The return value from field2json at line 32 is assigned to field_json and dereferenced without null check at line 33.


## Case 2

Is Reproduce: Yes

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


## Case 3

Is Reproduce: No

Program locations:

* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/pbjson.cc#L242
* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/pbjson.cc#L206

Bug traces:

* <        return NULL;, parse_msg>
* <parse_msg(value, allocator), field2json>

Explanation:

* The NULL value is directly returned to the caller of parse_msg function at line 5.
* The return value from parse_msg at line 157 is dereferenced at line 158 without null check.


## Case 4

Is Reproduce: No

Program locations:

* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/pbjson.cc#L242
* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/pbjson.cc#L214
* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/pbjson.cc#L269

Bug traces:

* <        return NULL;, parse_msg>
* <parse_msg(value, allocator), field2json>
* <field2json(msg, field, allocator), parse_msg>

Explanation:

* The NULL value is directly returned to the caller of parse_msg function at line 5.
* The return value from parse_msg at line 165 is assigned to json and returned to the caller at line 186.
* The return value from field2json at line 32 is assigned to field_json and dereferenced without null check at line 33.


## Case 5

Is Reproduce: No

Program locations:

* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/compressed_stream.cc#L34
* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/rpc_client_impl.cc#L431

Bug traces:

* <    return NULL;, get_compressed_input_stream>
* <get_compressed_input_stream(buffer.get(), compress_type), DoneCallback>

Explanation:

* The NULL value of `return NULL;` at line 19 is returned to the caller of the function `get_compressed_input_stream`. Thus the NULL value of `return NULL;` at line 19 propagates to the caller.
* The NULL value of `get_compressed_input_stream(buffer.get(), compress_type)` at line 22 propagates to the pointer `is` at line 21. The pointer `is` is dereferenced at line 23. Thus, there is a potential Null Pointer Dereference bug in the function `DoneCallback`.


## Case 6

Is Reproduce: No

Program locations:

* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/compressed_stream.cc#L34
* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/binary_rpc_request.cc#L91

Bug traces:

* <    return NULL;, get_compressed_input_stream>
* <get_compressed_input_stream(_req_body.get(), compress_type), ProcessRequest>

Explanation:

* The NULL value of `return NULL;` at line 19 is returned to the caller of the function `get_compressed_input_stream`. Thus the NULL value of `return NULL;` at line 19 propagates to the caller.
* The NULL value of `get_compressed_input_stream(_req_body.get(), compress_type)` at line 54 propagates to the pointer `is` at line 53. The pointer `is` is dereferenced at line 55. Thus, there is a potential Null Pointer Dereference bug in the function `ProcessRequest`.


## Case 7

Is Reproduce: No

Program locations:

* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/compressed_stream.cc#L65
* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/rpc_client_impl.cc#L304

Bug traces:

* <    return NULL;, get_compressed_output_stream>
* <get_compressed_output_stream(&write_buffer, meta.compress_type()), CallMethod>

Explanation:

* The NULL value of `return NULL;` at line 29 is returned to the caller of the function `get_compressed_output_stream`. Thus, the NULL value propagates to the caller.
* The NULL value of `get_compressed_output_stream(&write_buffer, meta.compress_type())` at line 92 propagates to the pointer `os` at line 91. The pointer `os` is dereferenced at line 93. Thus, there is a potential Null Pointer Dereference bug in the function `CallMethod`.


## Case 8

Is Reproduce: No

Program locations:

* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/compressed_stream.cc#L65
* https://github.com/baidu/sofa-pbrpc/tree/d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b/src/sofa/pbrpc/binary_rpc_request.cc#L160

Bug traces:

* <    return NULL;, get_compressed_output_stream>
* <get_compressed_output_stream(&write_buffer, meta.compress_type()), AssembleSucceedResponse>

Explanation:

* The NULL value of `return NULL;` at line 29 is returned to the caller of the function `get_compressed_output_stream`. Thus, the NULL value propagates to the caller.
* The NULL value of `get_compressed_output_stream(&write_buffer, meta.compress_type())` at line 35 propagates to the pointer `os` at line 34. The pointer `os` is dereferenced at line 36. Thus, there is a potential Null Pointer Dereference bug in the function `AssembleSucceedResponse`.


