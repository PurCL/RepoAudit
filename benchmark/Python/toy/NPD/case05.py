def test5_get_list():
    return [None] * 5

def test5_inner(lst):
    return lst[2].attr

def test5_middle(lst):
    return test5_inner(lst)

def test5_use_list():
    lst = test5_get_list()
    return test5_middle(lst)
