#include <iostream>

class Resource {
public:
    Resource() { std::cout << "Resource created\n"; }
    ~Resource() { std::cout << "Resource destroyed\n"; }
    int value = 42;
};

Resource* allocateAndFree() {
    Resource* res = new Resource();
    delete res;
    return res;
}

void useResource(Resource* res) {
    std::cout << "Resource value: " << res->value << "\n";
}

int main() {
    Resource* ptr = allocateAndFree();
    useResource(ptr);
    return 0;
}