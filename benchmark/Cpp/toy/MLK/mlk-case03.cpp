#include <iostream>
#include <stdexcept>

void initializeData(int* data, int size) {
    if (size > 1000) {
        throw std::runtime_error("Size too large");
    }
    
    for (int i = 0; i < size; i++) {
        data[i] = i;
    }
}

void processData(int size) {
    int* data = new int[size];
    
    try {
        initializeData(data, size);
    }
    catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return;
    }
    
    std::cout << "Data processed successfully" << std::endl;
    delete[] data;
}

int main() {
    processData(500); 
    processData(1500);
    return 0;
}