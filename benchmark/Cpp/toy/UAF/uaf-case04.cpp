#include <stdio.h>
#include <stdlib.h>

char* uaf_case04_initialize() {
    char* buffer = (char*)malloc(100);
    sprintf(buffer, "Hello, world!");
    printf("Buffer initialized: %s\n", buffer);
    return buffer;
}

void uaf_case04_conditional_cleanup(int condition, char* buffer) {
    if (condition) {
        printf("Cleaning up based on condition\n");
        if (buffer != NULL) {
            free(buffer);
        }
    }
}

void uaf_case04_use_buffer(char* buffer) {
    if (buffer != NULL) {
        printf("Using buffer: %s\n", buffer);
        sprintf(buffer, "Modified content");
    }
}

int uaf_case04_main(int argc, char *argv[]) {
    char* buffer = uaf_case04_initialize();

    int should_cleanup = (argc > 1) ? 1 : 0;
    uaf_case04_conditional_cleanup(should_cleanup, buffer);
    
    uaf_case04_use_buffer(buffer);
    
    return 0;
}