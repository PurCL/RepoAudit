#include <stdio.h>
#include <stdlib.h>

int test7_main() {
    int *ptr = NULL;
    int arr[5] = {1, 2, 3, 4, 5};
    
    if (ptr == NULL) {
        ptr = arr;
    }
    
    printf("Value: %d\n", *ptr);
    
    return 0;
}

int main() {
    test7_main();
}