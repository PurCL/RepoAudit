def test3_fetch_config(flag):
    if flag == True:
        return None
    else:
        return {"database_url": "url.com"}

def test3_get_setting():
    config = test3_fetch_config(True)
    return config.get("database_url")

def test3_setup_database():
    db_url = test3_get_setting()
    print(f"Connecting to: {db_url}")

test3_setup_database()