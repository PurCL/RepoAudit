#include <stdlib.h>

int* test4_voo() {
    return NULL;
}

int* test4_bar(int* ptr) {
    return ptr;
}

void test4_goo(int* ptr) {
    *ptr = 42; 
}

int test4_main() {
    int* ptr = test4_voo();
    ptr = test4_bar(ptr);
    test4_goo(ptr);
    return 0;
}

int main() {
    test4_main();
    return 0;
}