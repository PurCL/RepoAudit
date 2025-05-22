def test6_get_data():
    return {"Name": "Alice", "Age": 30}

def test6_get_email(data: dict):
    return data.pop("email", None)

def test6_main():
    data = test6_get_data()
    email = test6_get_email(data)
    username = email.split("@")[0]
    print(username)


if __name__ == "__main__":
    test6_main()