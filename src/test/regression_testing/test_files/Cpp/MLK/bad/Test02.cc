#include <iostream>
#include <cstring>

char* test2_processData(const char* input) {
    char* buffer = new char[100];
    
    if (input == nullptr) {
        return nullptr;
    }

    strcpy(buffer, input);
    return buffer;
}

void test2_handleRequest(const char* input) {
    char* result = test2_processData(input);
    
    if (result) {
        std::cout << "Result: " << result << std::endl;
    }
}

int test2_main() {
    test2_handleRequest("Hello");
    test2_handleRequest(nullptr);
    return 0;
}

int main() {
    test2_main();
    return 0;
}