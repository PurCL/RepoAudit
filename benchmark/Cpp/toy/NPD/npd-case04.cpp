#include <stdlib.h>

int* voo() {
    return NULL;
}

int* bar(int* ptr) {
    return ptr;
}

void goo(int* ptr) {
    *ptr = 42; 
}

int main() {
    int* ptr = voo();
    ptr = bar(ptr);
    goo(ptr);
    return 0;
}