#include <iostream>

char* test2_allocateMemory(int size) {
    char* buffer = new char[size];
    std::cout << "Memory allocated with size: " << size << std::endl;
    return buffer;
}

void test2_processData(bool shouldFree, char* buffer) {
    if (buffer) {
        buffer[0] = 'A';
        
        if (shouldFree) {
            free(buffer);
            std::cout << "Memory freed" << std::endl;
        }
    }
}

void test2_useBuffer(char* buffer) {
    if (buffer) {
        std::cout << "First character: " << buffer[0] << std::endl;
    }
}

int test2_main(int argc, char* argv[]) {
    char* buffer = test2_allocateMemory(100);
    test2_processData(true, buffer);  
    test2_useBuffer(buffer);       
    return 0;
}

int main() {
    test2_main();
    return 0;
}