#include <iostream>
#include <cstdlib>

int test6_main() {
    int *data = new int[5];
    data[0] = 42;
    
    std::cout << "Original: " << data[0] << std::endl;
    
    delete[] data;
    
    data = new int[5];
    data[0] = 100;
    
    std::cout << "New: " << data[0] << std::endl;
    
    delete[] data;
    return 0;
}

int main() {
    test6_main();
    return 0;
}