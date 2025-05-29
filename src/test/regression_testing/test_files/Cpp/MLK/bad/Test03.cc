#include <iostream>
#include <stdexcept>

void test3_initializeData(int* data, int size) {
    if (size > 1000) {
        throw std::runtime_error("Size too large");
    }
    
    for (int i = 0; i < size; i++) {
        data[i] = i;
    }
}

void test3_processData(int size) {
    int* data = new int[size];
    
    try {
        test3_initializeData(data, size);
    }
    catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return;
    }
    
    std::cout << "Data processed successfully" << std::endl;
    free(data);
}

int main() {
    test3_processData(500); 
    test3_processData(1500);
    return 0;
}