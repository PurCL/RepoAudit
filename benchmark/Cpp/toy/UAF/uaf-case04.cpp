#include <stdio.h>
#include <stdlib.h>

char* initialize() {
    char* buffer = (char*)malloc(100);
    sprintf(buffer, "Hello, world!");
    printf("Buffer initialized: %s\n", buffer);
    return buffer;
}

void conditional_cleanup(int condition, char* buffer) {
    if (condition) {
        printf("Cleaning up based on condition\n");
        if (buffer != NULL) {
            free(buffer);
        }
    }
}

void use_buffer(char* buffer) {
    if (buffer != NULL) {
        printf("Using buffer: %s\n", buffer);
        sprintf(buffer, "Modified content");
    }
}

int main(int argc, char *argv[]) {
    char* buffer = initialize();

    int should_cleanup = (argc > 1) ? 1 : 0;
    conditional_cleanup(should_cleanup, buffer);
    
    use_buffer(buffer);
    
    return 0;
}