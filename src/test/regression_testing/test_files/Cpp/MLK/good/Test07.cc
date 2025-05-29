#include <iostream>
#include <cstdlib>

int test7_main() {
    int *buffer;
    int choice = 1;
    
    if (choice == 1) {
        buffer = new int[5];
        buffer[0] = 100;
    } else {
        buffer = new int[3];
        buffer[0] = 200;
    }
    
    std::cout << "Buffer: " << buffer[0] << std::endl;
    
    if (choice == 1) {
        delete[] buffer;
    } else {
        delete[] buffer;
    }
    
    return 0;
}

int main() {
    test7_main();
    return 0;
}