#include <iostream>

void test1_bar(int* ptr) {
    std::cout << "Value: " << *ptr << std::endl;
}

void test1_xoo() {
    int* data = new int(42);
    test1_bar(data);
}

int test1_main() {
    test1_xoo();
    return 0;
}

int main() {
    test1_main();
    return 0;
}