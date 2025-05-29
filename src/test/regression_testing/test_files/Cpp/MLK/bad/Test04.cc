#include <iostream>
#include <string>

char* test4_allocateBuffer(int size) {
    return new char[size];
}

bool test4_processBuffer(char* buffer, const std::string& data) {
    if (data.empty()) {
        std::cout << "Empty data, skipping processing" << std::endl;
        return false;
    }
    
    std::cout << "Processing data: " << data << std::endl;
    return true;
}

void test4_handleData(const std::string& data) {
    char* buffer = test4_allocateBuffer(1024);
    
    bool success = test4_processBuffer(buffer, data);
    
    if (success) {
        std::cout << "Processing completed successfully" << std::endl;
        free(buffer);
    }
}

int test4_main() {
    test4_handleData("Hello World");  
    test4_handleData("");              
    return 0;
}

int main() {
    test4_main();
    return 0;
}