#include <iostream>

class Resource {
public:
    Resource() { std::cout << "Resource created\n"; }
    ~Resource() { std::cout << "Resource destroyed\n"; }
    int value = 42;
};

Resource* test1_allocateAndFree() {
    Resource* res = new Resource();
    free(res);
    return res;
}

void test1_useResource(Resource* res) {
    std::cout << "Resource value: " << res->value << "\n";
}

int test1_main() {
    Resource* ptr = test1_allocateAndFree();
    test1_useResource(ptr);
    return 0;
}

int main() {
    test1_main();
    return 0;
}