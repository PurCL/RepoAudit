#include <stdlib.h>

int* npd_case_04_voo() {
    return NULL;
}

int* npd_case_04_bar(int* ptr) {
    return ptr;
}

void npd_case_04_goo(int* ptr) {
    *ptr = 42; 
}

int npd_case_04_main() {
    int* ptr = npd_case_04_voo();
    ptr = npd_case_04_bar(ptr);
    npd_case_04_goo(ptr);
    return 0;
}