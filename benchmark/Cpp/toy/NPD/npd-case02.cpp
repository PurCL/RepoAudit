#include <stdlib.h>

int* npd_case_02_foo(int x) {
    if (x > 10) {
        return malloc(sizeof(int));
    } else {
        return NULL;
    }
}

void npd_case_02_goo(int* ptr) {
    *ptr = 42;
}

int npd_case_02_main() {
    int* ptr = npd_case_02_foo(5);
    npd_case_02_goo(ptr);
    return 0;
}