#include <iostream>

char* uaf_case02_allocateMemory(int size) {
    char* buffer = new char[size];
    std::cout << "Memory allocated with size: " << size << std::endl;
    return buffer;
}

void uaf_case02_processData(bool shouldFree, char* buffer) {
    if (buffer) {
        buffer[0] = 'A';
        
        if (shouldFree) {
            free(buffer);
            std::cout << "Memory freed" << std::endl;
        }
    }
}

void uaf_case02_useBuffer(char* buffer) {
    if (buffer) {
        std::cout << "First character: " << buffer[0] << std::endl;
    }
}

int uaf_case02_main(int argc, char* argv[]) {
    char* buffer = uaf_case02_allocateMemory(100);
    uaf_case02_processData(true, buffer);  
    uaf_case02_useBuffer(buffer);       
    return 0;
}