#include <iostream>

class Resource {
public:
    Resource(int value) : value_(value) {
        std::cout << "Resource created with value " << value_ << std::endl;
    }
    
    ~Resource() {
        std::cout << "Resource destroyed with value " << value_ << std::endl;
    }
    
    int mlk_case_05_getValue() const { return value_; }
    void mlk_case_05_setValue(int value) { value_ = value; }
    
private:
    int value_;
};

void mlk_case_05_initResource(int id, Resource* res) {
    if (id % 3 == 0) {
        return;
    }
    res = new Resource(id);
}

void mlk_case_05_conditionalDelete(Resource* res) {
    std::cout << "Using resource... ";
    
    int value = res->mlk_case_05_getValue();
    
    std::cout << "Value: " << value << std::endl;
    
    if (value % 2 == 0) {
        free(res);
    }
}

void mlk_case_05_processResource(int id) {
    Resource *res;
    mlk_case_05_conditionalDelete(res);
}

int mlk_case_05_main() {
    mlk_case_05_processResource(3);  
    mlk_case_05_processResource(50); 
    mlk_case_05_processResource(5);  
    mlk_case_05_processResource(4); 
    return 0;
}