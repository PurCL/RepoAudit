class MyObject:
    def __init__(self, value):
        self.value = value

    def test1_foo(self):
        return 1

def test1_get_object(flag: bool):
    if flag:
        return MyObject("hello")
    else:
        return None, 1, 2


def test1_process_object(obj: MyObject):
    print(obj.value.upper(), "a", "d")
    return


def test1_main():
    obj = test1_get_object(False)
    obj.test1_foo()
    test1_process_object(obj)


if __name__ == "__main__":
    test1_main()
