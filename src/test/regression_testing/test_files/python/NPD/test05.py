def test5_get_data():
    return {"Name": "Alice", "Age": 30}


def test5_get_phone(data: dict):
    return data.get("Phone Number")


def test5_main():
    data = test5_get_data()
    phone_number = test5_get_phone(data)
    phone_number_no_area_code = phone_number[:3]  # cut off first 3 chars
    print(phone_number_no_area_code)


if __name__ == "__main__":
    test5_main()
