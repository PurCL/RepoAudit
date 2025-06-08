def test9_get_attr(value):
    if hasattr(value, "upper"):
        return value.upper()
    else:
        return None


def test9_call(value):
    if callable(value):
        return value()
    else:
        return None


def test9_type(value):
    return type(value)


def test9_instance(value):
    return isinstance(value, str)


def test9_main():
    value = None
    print(test9_get_attr(value))
    print(test9_call(value))
    print(test9_type(value))
    print(test9_instance(value))


if __name__ == "__main__":
    test9_main()
