users = ['Alice', 'Bob', 'Charlie']

def test4_find_user_index(name):
    try:
        return users.index(name)
    except ValueError:
        return None

idx = test4_find_user_index('Dave')
next_user = users[idx + 1]