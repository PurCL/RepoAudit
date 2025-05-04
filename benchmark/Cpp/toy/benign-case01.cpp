#include <iostream>

using namespace std;

void zoo(int x) {
    cout << "free function foo called with " << x << endl;
}

class A {
public:
    struct Helper {
        Helper* g00() {
            return nullptr;
        }
        Helper* goo() {
            return nullptr;
        }
        Helper* operator->() {
            return this;
        }
    };

    Helper foo() {
        return Helper();
    }

    Helper* foo_ptr() {
        return nullptr;
    }
};

A* bar() {
    return nullptr;
}

int main() {
    zoo(42);

    A a;
    A* a_ptr = &a;

    A::Helper helper1 = a.foo();
    A::Helper* null_helper1 = helper1.g00();
    if (null_helper1) {
        null_helper1->goo();
    } else {
        cout << "Bug: a.foo().g00() returned a null pointer" << endl;
    }

    A::Helper helper2 = a_ptr->foo();
    A::Helper* null_helper2 = helper2.g00();
    if (null_helper2) {
        null_helper2->goo();
    } else {
        cout << "Bug: a->foo().g00() returned a null pointer" << endl;
    }

    A::Helper* null_helper3 = a.foo()->goo();
    if (null_helper3) {
        null_helper3->goo();
    } else {
        cout << "Bug: a.foo()->goo() returned a null pointer" << endl;
    }

    A* bug_a_ptr = bar();
    if (bug_a_ptr) {
        A::Helper* shouldBeNull = bug_a_ptr->foo_ptr();
        if (shouldBeNull)
            shouldBeNull->goo();
    } else {
        cout << "Bug: bar() returned a null pointer" << endl;
    }

    return 0;
}