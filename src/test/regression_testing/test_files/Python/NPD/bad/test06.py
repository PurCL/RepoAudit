def test6_load_data(flag):
    if flag == True:
        return {"key": "val"}
    else:
        return None


def test6_get_item():
    collection = test6_load_data(False)
    return collection["key"]


def test6_display():
    item = test6_get_item()
    print(item)


test6_display()
