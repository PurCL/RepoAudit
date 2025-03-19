#include <stdlib.h>

int* foo() {
    return NULL;
}

void goo(int* ptr) {
    *ptr = 42;
}

int main() {
    int* ptr = foo();
    goo(ptr);
    return 0;
}