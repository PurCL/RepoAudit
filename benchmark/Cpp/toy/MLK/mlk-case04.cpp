#include <iostream>
#include <string>

char* mlk_case_04_allocateBuffer(int size) {
    return new char[size];
}

bool mlk_case_04_processBuffer(char* buffer, const std::string& data) {
    if (data.empty()) {
        std::cout << "Empty data, skipping processing" << std::endl;
        return false;
    }
    
    std::cout << "Processing data: " << data << std::endl;
    return true;
}

void mlk_case_04_handleData(const std::string& data) {
    char* buffer = mlk_case_04_allocateBuffer(1024);
    
    bool success = mlk_case_04_processBuffer(buffer, data);
    
    if (success) {
        std::cout << "Processing completed successfully" << std::endl;
        free(buffer);
    }
}

int mlk_case_04_main() {
    mlk_case_04_handleData("Hello World");  
    mlk_case_04_handleData("");              
    return 0;
}