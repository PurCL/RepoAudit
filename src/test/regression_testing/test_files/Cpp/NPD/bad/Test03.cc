#include <stdlib.h>

typedef struct {
    int* data;
} Container;

Container* test3_moo() {
    Container* c = (Container*)malloc(sizeof(Container));
    c->data = NULL; 
    return c;
}

void test3_goo(Container* c) {
    *(c->data) = 42; 
}

int test3_main() {
    Container* container = test3_moo();
    test3_goo(container);
    free(container);
    return 0;
}

int main() {
    test3_main();
    return 0;
}