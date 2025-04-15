#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    int id;
    char* name;
} User;

User* uaf_case05_create_user(int id, const char* name) {
    User* g_user = (User*)malloc(sizeof(User));
    g_user->id = id;
    g_user->name = (char*)malloc(strlen(name) + 1);
    strcpy(g_user->name, name);
    printf("User created: ID=%d, Name=%s\n", id, name);
    return g_user;
}

void uaf_case05_delete_user(User* g_user) {
    if (g_user) {
        free(g_user->name);
        free(g_user);
        printf("User deleted\n");
    }
}

void uaf_case05_display_user(User* g_user) {
    if (g_user) {
        printf("User: ID=%d, Name=%s\n", g_user->id, g_user->name);
    } else {
        printf("No user available\n");
    }
}

void uaf_case05_process_user(User* g_user) {
    uaf_case05_display_user(g_user);
    uaf_case05_delete_user(g_user);
}

void uaf_case05_update_user_state(User* g_user) {
    if (g_user) {
        g_user->id += 1;
        printf("User ID updated\n");
    }
}

int uaf_case05_main() {
    User* g_user = uaf_case05_create_user(1, "Test User");
    uaf_case05_process_user(g_user);      
    uaf_case05_update_user_state(g_user); 
    uaf_case05_display_user(g_user);     
    return 0;
}