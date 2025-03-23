#include <iostream>

char* allocateMemory(int size) {
    char* buffer = new char[size];
    std::cout << "Memory allocated with size: " << size << std::endl;
    return buffer;
}

void processData(bool shouldFree, char* buffer) {
    if (buffer) {
        buffer[0] = 'A';
        
        if (shouldFree) {
            delete[] buffer;
            std::cout << "Memory freed" << std::endl;
        }
    }
}

void useBuffer(char* buffer) {
    if (buffer) {
        std::cout << "First character: " << buffer[0] << std::endl;
    }
}

int main(int argc, char* argv[]) {
    char* buffer = allocateMemory(100);
    processData(true, buffer);  
    useBuffer(buffer);       
    return 0;
}