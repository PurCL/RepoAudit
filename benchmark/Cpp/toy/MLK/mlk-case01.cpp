#include <iostream>

void mlk_case_01_bar(int* ptr) {
    std::cout << "Value: " << *ptr << std::endl;
}

void mlk_case_01_xoo() {
    int* data = new int(42);
    mlk_case_01_bar(data);
}

int mlk_case_01_main() {
    mlk_case_01_xoo();
    return 0;
}