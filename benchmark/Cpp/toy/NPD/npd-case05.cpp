#include <stdlib.h>

int* npd_case_05_foo(int flag) {
    if (flag) {
        return (int*)malloc(sizeof(int));
    }
    return NULL;
}

void npd_case_05_process(int* ptr) {
   
}

void npd_case_05_goo(int* ptr, int val) {
    if (val > 10) {
        npd_case_05_process(ptr);
    }
    *ptr = 42;
}

int npd_case_05_main() {
    int* ptr = npd_case_05_foo(0);
    npd_case_05_goo(ptr, 15);
    return 0;
}