#include <stdio.h>
#include <stdlib.h>

typedef void (*callback_t)(void);

typedef struct {
    callback_t callback;
    int data;
} Handler;

void test3_actual_callback() {
    printf("Callback executed\n");
}

Handler* test3_create_handler() {
    Handler* handler = (Handler*)malloc(sizeof(Handler));
    handler->callback = test3_actual_callback;
    handler->data = 42;
    printf("Handler created\n");
    return handler;
}

void test3_destroy_handler(Handler* handler) {
    if (handler != NULL) {
        free(handler);
        printf("Handler destroyed\n");
    }
}

void test3_execute_callback(Handler* handler) {
    if (handler != NULL) {
        handler->callback();
        printf("Handler data: %d\n", handler->data);
    }
}

int test3_main() {
    Handler* handler = test3_create_handler();
    test3_destroy_handler(handler);
    test3_execute_callback(handler);
    return 0;
}

int main() {
    test3_main();
    return 0;
}