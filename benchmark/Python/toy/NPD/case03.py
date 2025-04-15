def test3_get_data():
    return None

def test3_transform_data(data):
    return data.upper()  # Attempting to call method on None

def test3_main():
    data = test3_get_data()
    return test3_transform_data(data)  # Null dereference
