#include <iostream>

class Resource {
public:
    Resource(int value) : value_(value) {
        std::cout << "Resource created with value " << value_ << std::endl;
    }
    
    ~Resource() {
        std::cout << "Resource destroyed with value " << value_ << std::endl;
    }
    
    int getValue() const { return value_; }
    void setValue(int value) { value_ = value; }
    
private:
    int value_;
};

void initResource(int id, Resource* res) {
    if (id % 3 == 0) {
        return;
    }
    res = new Resource(id);
}

void conditionalDelete(Resource* res) {
    std::cout << "Using resource... ";
    
    int value = res->getValue();
    
    std::cout << "Value: " << value << std::endl;
    
    if (value % 2 == 0) {
        delete res;
    }
}

void processResource(int id) {
    Resource *res;
    conditionalDelete(res);
}

int main() {
    processResource(3);  
    processResource(50); 
    processResource(5);  
    processResource(4); 
    return 0;
}