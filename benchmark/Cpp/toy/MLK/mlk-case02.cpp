#include <iostream>
#include <cstring>

char* processData(const char* input) {
    char* buffer = new char[100];
    
    if (input == nullptr) {
        return nullptr;
    }

    strcpy(buffer, input);
    return buffer;
}

void handleRequest(const char* input) {
    char* result = processData(input);
    
    if (result) {
        std::cout << "Result: " << result << std::endl;
    }
}

int main() {
    handleRequest("Hello");
    handleRequest(nullptr);
    return 0;
}