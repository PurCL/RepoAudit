def test7_get_resource():
    resource = None
    return resource


def test7_use_resource():
    r = test7_get_resource()
    return r.close()


def test7_cleanup_resources():
    test7_use_resource()
    print("Cleanup complete")


test7_cleanup_resources()
