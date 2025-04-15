#include <stdlib.h>

typedef struct {
    int* data;
} Container;

Container* npd_case_03_moo() {
    Container* c = (Container*)malloc(sizeof(Container));
    c->data = NULL; 
    return c;
}

void npd_case_03_goo(Container* c) {
    *(c->data) = 42; 
}

int npd_case_03_main() {
    Container* container = npd_case_03_moo();
    npd_case_03_goo(container);
    free(container);
    return 0;
}