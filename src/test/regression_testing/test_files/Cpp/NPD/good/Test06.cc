#include <stdio.h>
#include <stdlib.h>

int test6_main() {
    int data = 42;
    int *ptr = NULL;
    
    ptr = &data;
    ptr = ptr - 1;
    ptr = ptr + 1;
    
    printf("Value: %d\n", *ptr);
    
    return 0;
}

int main() {
    test6_main();
    return 0;
}