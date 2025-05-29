#include <iostream>
#include <cstdlib>

int test7_main() {
    int *ptr = new int(25);
    int *backup = new int(50);
    
    std::cout << "Ptr: " << *ptr << std::endl;
    
    delete ptr;
    
    ptr = backup;
    
    std::cout << "Ptr after reassign: " << *ptr << std::endl;
    
    delete ptr;
    return 0;
}

int main() {
    test7_main();
    return 0;
}