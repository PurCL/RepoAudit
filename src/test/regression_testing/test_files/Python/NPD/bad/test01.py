def test1_get_user_data():
    user = None
    return user


def test1_process_user():
    user_obj = test1_get_user_data()
    return user_obj.get("name")


def test1_main():
    result = test1_process_user()
    print(f"User name: {result}")


test1_main()
