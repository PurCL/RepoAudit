def test2_get_empty_list():
    data = None
    return data


def test2_access_element():
    my_list = test2_get_empty_list()
    return my_list[0]


def test2_display_result():
    element = test2_access_element()
    print(f"First element: {element}")


test2_display_result()
