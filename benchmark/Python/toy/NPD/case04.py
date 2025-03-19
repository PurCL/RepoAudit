class Test4_Example:
    def __init__(self, value):
        self.value = value
    
    def get_value(self):
        return self.value.attr  # Null dereference

def test4_inner_call(obj):
    return obj.get_value()

def test4_middle_call(obj):
    return test4_inner_call(obj)

def test4_test():
    obj = Test4_Example(None)
    return test4_middle_call(obj)