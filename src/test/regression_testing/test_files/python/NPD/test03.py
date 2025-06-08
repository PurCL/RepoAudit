import attrs


class Test3MyObject:

    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value.attr


def test3_inner_3(obj: Test3MyObject):
    return obj.get_value()


def test3_inner_2(obj: Test3MyObject):
    return test3_inner_3(obj)


def test3_inner_1(obj: Test3MyObject):
    return test3_inner_2(obj)


if __name__ == "__main__":
    obj = Test3MyObject(None)
    print(test3_inner_1(obj))
