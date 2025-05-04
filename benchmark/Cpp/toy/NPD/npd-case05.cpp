#include <stdlib.h>

int* foo(int flag) {
    if (flag) {
        return (int*)malloc(sizeof(int));
    }
    return NULL;
}

void process(int* ptr) {
   
}

void goo(int* ptr, int val) {
    if (val > 10) {
        process(ptr);
    }
    *ptr = 42;
}

int main() {
    int* ptr = foo(0);
    goo(ptr, 15);
    return 0;
}