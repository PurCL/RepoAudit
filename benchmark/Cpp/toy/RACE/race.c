//gcc chall.c -m32 -pie -fstack-protector-all -o chall

#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include <pthread.h>

unsigned int a = 0;
unsigned int b = 0;
unsigned int a_sleep = 0;
int flag = 1;
int pstr1 = 1;
int ret1;
pthread_t th1;
void * th_ret = NULL;

void menu_go(){
    if(a_sleep == 0){
        a = a + 5;
    }else{
        a_sleep = 0;
    }

    b = b + 2;
}

int *menu_chance(){
    if(a<=b){
        puts("No");
        return 0;
    }

    if(flag == 1){
        a_sleep = 1;
        sleep(1);
        flag = 0;
    }
    else{
        puts("Only have one chance");
    }
    return 0;
}


void menu_test(){
    if( b>a ){
        puts("Win!");
        system("/bin/sh");
        exit(0);
    }else{
        puts("Lose!");
        exit(0);
    }
}

void menu_exit(){
    puts("Bye");
    exit(0);
}

void menu(){
    printf("***** race *****\n");
    printf("*** 1:Go\n*** 2:Chance\n*** 3:Test\n*** 4:Exit \n");
    printf("*************************************\n");
    printf("Choice> ");
    int choose;
    scanf("%d",&choose);
    switch(choose)
    {
    case 1:
        menu_go();
        break;
    case 2:
        ret1 = pthread_create(&th1, NULL, menu_chance, &pstr1);
        break;
    case 3:
        menu_test();
        break;
    case 4:
        menu_exit();
        break;
    default:
        return;
    }
    return;

}


void init(){
    setbuf(stdin, 0LL);
    setbuf(stdout, 0LL);
    setbuf(stderr, 0LL);

    while (1)
    {
        menu();
    }
    
}

int main(){
    init();
    return 0;
}

