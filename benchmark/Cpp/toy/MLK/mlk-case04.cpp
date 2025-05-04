#include <iostream>
#include <string>

char* allocateBuffer(int size) {
    return new char[size];
}

bool processBuffer(char* buffer, const std::string& data) {
    if (data.empty()) {
        std::cout << "Empty data, skipping processing" << std::endl;
        return false;
    }
    
    std::cout << "Processing data: " << data << std::endl;
    return true;
}

void handleData(const std::string& data) {
    char* buffer = allocateBuffer(1024);
    
    bool success = processBuffer(buffer, data);
    
    if (success) {
        std::cout << "Processing completed successfully" << std::endl;
        delete[] buffer;
    }
}

int main() {
    handleData("Hello World");  
    handleData("");              
    return 0;
}