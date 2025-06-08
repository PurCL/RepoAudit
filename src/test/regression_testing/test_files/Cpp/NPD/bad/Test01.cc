#include <stdlib.h>

int* test1_foo() {
    return NULL;
}

void test1_goo(int* ptr) {
    *ptr = 42;
}

int test1_main() {
    int* ptr = test1_foo();
    test1_goo(ptr);
    return 0;
}

int main() {
    test1_main();
    return 0;
}