#include <stdio.h>
#include <stdlib.h>

typedef void (*callback_t)(void);

typedef struct {
    callback_t callback;
    int data;
} Handler;

void uaf_case03_actual_callback() {
    printf("Callback executed\n");
}

Handler* uaf_case03_create_handler() {
    Handler* handler = (Handler*)malloc(sizeof(Handler));
    handler->callback = uaf_case03_actual_callback;
    handler->data = 42;
    printf("Handler created\n");
    return handler;
}

void uaf_case03_destroy_handler(Handler* handler) {
    if (handler != NULL) {
        free(handler);
        printf("Handler destroyed\n");
    }
}

void uaf_case03_execute_callback(Handler* handler) {
    if (handler != NULL) {
        handler->callback();
        printf("Handler data: %d\n", handler->data);
    }
}

int uaf_case03_main() {
    Handler* handler = uaf_case03_create_handler();
    uaf_case03_destroy_handler(handler);
    uaf_case03_execute_callback(handler);
    return 0;
}