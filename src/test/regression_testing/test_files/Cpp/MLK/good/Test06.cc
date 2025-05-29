#include <iostream>
#include <cstdlib>

int test6_main() {
    int *data = new int[10];
    
    if (data == nullptr) {
        return 1;
    }
    
    data[0] = 42;
    
    if (data[0] > 0) {
        std::cout << "Value: " << data[0] << std::endl;
        delete[] data;
        return 0;
    }
    
    delete[] data;
    return 0;
}

int main() {
    test6_main();
    return 0;
}