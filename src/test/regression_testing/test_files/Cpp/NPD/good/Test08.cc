#include <stdio.h>
#include <stdlib.h>

void test8_process_data(int *ptr) {
    static int default_value = 100;
    
    if (ptr == NULL) {
        ptr = &default_value;
    }
    
    printf("Processing: %d\n", *ptr);
}

int test_8main() {
    int *null_ptr = NULL;
    
    test8_process_data(null_ptr);
    
    return 0;
}

int main() {
    test8_main();
    return 0;
}