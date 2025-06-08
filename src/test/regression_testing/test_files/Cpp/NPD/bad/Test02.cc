#include <stdlib.h>

int* test2_foo(int x) {
    if (x > 10) {
        return malloc(sizeof(int));
    } else {
        return NULL;
    }
}

void test2_goo(int* ptr) {
    *ptr = 42;
}

int test2_main() {
    int* ptr = test2_foo(5);
    test2_goo(ptr);
    return 0;
}

int main() {
    test2_main();
    return 0;
}