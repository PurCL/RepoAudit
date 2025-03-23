#include <stdio.h>
#include <stdlib.h>

typedef void (*callback_t)(void);

typedef struct {
    callback_t callback;
    int data;
} Handler;

void actual_callback() {
    printf("Callback executed\n");
}

Handler* create_handler() {
    Handler* handler = (Handler*)malloc(sizeof(Handler));
    handler->callback = actual_callback;
    handler->data = 42;
    printf("Handler created\n");
    return handler;
}

void destroy_handler(Handler* handler) {
    if (handler != NULL) {
        free(handler);
        printf("Handler destroyed\n");
    }
}

void execute_callback(Handler* handler) {
    if (handler != NULL) {
        handler->callback();
        printf("Handler data: %d\n", handler->data);
    }
}

int main() {
    Handler* handler = create_handler();
    destroy_handler(handler);
    execute_callback(handler);
    return 0;
}