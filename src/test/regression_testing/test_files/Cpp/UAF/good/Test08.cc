#include <iostream>
#include <cstdlib>

int test8_main() {
    int *buffer = new int[3];
    buffer[0] = 10;
    buffer[1] = 20;
    
    std::cout << "Buffer[0]: " << buffer[0] << std::endl;
    
    delete[] buffer;
    buffer = nullptr;
    
    buffer = new int[3];
    buffer[0] = 30;
    
    std::cout << "New buffer[0]: " << buffer[0] << std::endl;
    
    delete[] buffer;
    return 0;
}

int main() {
    test8_main();
    return 0;
}