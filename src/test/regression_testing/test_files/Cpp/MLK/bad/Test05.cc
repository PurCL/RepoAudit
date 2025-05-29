#include <iostream>

class Resource {
public:
    Resource(int value) : value_(value) {
        std::cout << "Resource created with value " << value_ << std::endl;
    }
    
    ~Resource() {
        std::cout << "Resource destroyed with value " << value_ << std::endl;
    }
    
    int test5_getValue() const { return value_; }
    void test5_setValue(int value) { value_ = value; }
    
private:
    int value_;
};

void test5_initResource(int id, Resource* res) {
    if (id % 3 == 0) {
        return;
    }
    res = new Resource(id);
}

void test5_conditionalDelete(Resource* res) {
    std::cout << "Using resource... ";
    
    int value = res->test5_getValue();
    
    std::cout << "Value: " << value << std::endl;
    
    if (value % 2 == 0) {
        free(res);
    }
}

void test5_processResource(int id) {
    Resource *res;
    test5_conditionalDelete(res);
}

int test5_main() {
    test5_processResource(3);  
    test5_processResource(50); 
    test5_processResource(5);  
    test5_processResource(4); 
    return 0;
}

int main() {
    test5_main();
    return 0;
}