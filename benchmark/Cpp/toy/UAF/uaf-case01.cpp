#include <iostream>

class Resource {
public:
    Resource() { std::cout << "Resource created\n"; }
    ~Resource() { std::cout << "Resource destroyed\n"; }
    int value = 42;
};

Resource* uaf_case01_allocateAndFree() {
    Resource* res = new Resource();
    free(res);
    return res;
}

void uaf_case01_useResource(Resource* res) {
    std::cout << "Resource value: " << res->value << "\n";
}

int uaf_case01_main() {
    Resource* ptr = uaf_case01_allocateAndFree();
    uaf_case01_useResource(ptr);
    return 0;
}