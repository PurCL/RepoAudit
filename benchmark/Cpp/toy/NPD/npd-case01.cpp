#include <stdlib.h>

int* npd_case_01_foo() {
    return NULL;
}

void npd_case_01_goo(int* ptr) {
    *ptr = 42;
}

int npd_case_01_main() {
    int* ptr = npd_case_01_foo();
    npd_case_01_goo(ptr);
    return 0;
}