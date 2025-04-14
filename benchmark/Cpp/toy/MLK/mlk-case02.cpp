#include <iostream>
#include <cstring>

char* mlk_case_02_processData(const char* input) {
    char* buffer = new char[100];
    
    if (input == nullptr) {
        return nullptr;
    }

    strcpy(buffer, input);
    return buffer;
}

void mlk_case_02_handleRequest(const char* input) {
    char* result = mlk_case_02_processData(input);
    
    if (result) {
        std::cout << "Result: " << result << std::endl;
    }
}

int mlk_case_02_main() {
    mlk_case_02_handleRequest("Hello");
    mlk_case_02_handleRequest(nullptr);
    return 0;
}