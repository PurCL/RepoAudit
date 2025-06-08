def test5_get_handler():
    handler = None
    return handler


def test5_process_data():
    h = test5_get_handler()
    return h.process("data")


def test5_execute():
    result = test5_process_data()
    print(result)


if __name__ == "__main__":
    test5_execute()
