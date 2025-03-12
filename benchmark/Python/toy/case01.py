class MyObject:
    def __init__(self, value):
        self.value = value

    def foo(self):
        return 1

def get_object(flag: bool):
    if flag:
        return MyObject("hello")
    else:
        return None


def process_object(obj: MyObject):
    print(obj.value.upper(), "a", "d")


def main():
    obj = get_object(False)
    obj.foo()
    process_object(obj)


if __name__ == "__main__":
    main()