#include <iostream>
#include <cstdlib>

int test8_main() {
    for (int i = 0; i < 3; i++) {
        int *temp = new int[i + 1];
        temp[0] = i * 10;
        
        std::cout << "Temp: " << temp[0] << std::endl;
        
        if (i >= 0) {
            delete[] temp;
        }
    }
    
    return 0;
}

int main() {
    test8_main();
    return 0;
}