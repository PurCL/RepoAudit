#include <stdio.h>
#include <stdlib.h>

char* test4_initialize() {
    char* buffer = (char*)malloc(100);
    sprintf(buffer, "Hello, world!");
    printf("Buffer initialized: %s\n", buffer);
    return buffer;
}

void test4_conditional_cleanup(int condition, char* buffer) {
    if (condition) {
        printf("Cleaning up based on condition\n");
        if (buffer != NULL) {
            free(buffer);
        }
    }
}

void test4_use_buffer(char* buffer) {
    if (buffer != NULL) {
        printf("Using buffer: %s\n", buffer);
        sprintf(buffer, "Modified content");
    }
}

int test4_main(int argc, char *argv[]) {
    char* buffer = test4_initialize();

    int should_cleanup = (argc > 1) ? 1 : 0;
    test4_conditional_cleanup(should_cleanup, buffer);
    
    test4_use_buffer(buffer);
    
    return 0;
}

int main(int argc, char *argv[]) {
    test4_main(argc, argv);
    return 0;
}