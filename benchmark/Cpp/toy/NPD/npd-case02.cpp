#include <stdlib.h>

int* foo(int x) {
    if (x > 10) {
        return malloc(sizeof(int));
    } else {
        return NULL;
    }
}

void goo(int* ptr) {
    *ptr = 42;
}

int main() {
    int* ptr = foo(5);
    goo(ptr);
    return 0;
}