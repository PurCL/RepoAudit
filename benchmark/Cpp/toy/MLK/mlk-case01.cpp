#include <iostream>

void bar(int* ptr) {
    std::cout << "Value: " << *ptr << std::endl;
}

void xoo() {
    int* data = new int(42);
    bar(data);
}

int main() {
    xoo();
    return 0;
}