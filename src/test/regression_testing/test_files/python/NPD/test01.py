def test1_foo(value: bool):
    if value == True:
        return None
    else:
        return "This is a string"


def test1_main():
    value = test1_foo(True)
    print(value.upper())


if __name__ == "__main__":
    test1_main()
