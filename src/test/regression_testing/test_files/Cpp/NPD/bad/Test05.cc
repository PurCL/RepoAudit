#include <stdlib.h>

int* test5_foo(int flag) {
    if (flag) {
        return (int*)malloc(sizeof(int));
    }
    return NULL;
}

void test5_process(int* ptr) {
   
}

void test5_goo(int* ptr, int val) {
    if (val > 10) {
        test5_process(ptr);
    }
    *ptr = 42;
}

int test5_main() {
    int* ptr = test5_foo(0);
    test5_goo(ptr, 15);
    return 0;
}

int main() {
    test5_main();
    return 0;
}