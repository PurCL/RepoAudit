def test7_get_list():
    return [3, 1, 4, 5]


def test7_sort_list(lis: list):
    return lis.sort()


def test7_main():
    li = test7_get_list()
    sorted_list = test7_sort_list(li)
    first_num = sorted_list[0]
    print(first_num)


test7_main()
