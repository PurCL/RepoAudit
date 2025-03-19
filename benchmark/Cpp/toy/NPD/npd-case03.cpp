#include <stdlib.h>

typedef struct {
    int* data;
} Container;

Container* moo() {
    Container* c = (Container*)malloc(sizeof(Container));
    c->data = NULL; 
    return c;
}

void goo(Container* c) {
    *(c->data) = 42; 
}

int main() {
    Container* container = moo();
    goo(container);
    free(container);
    return 0;
}