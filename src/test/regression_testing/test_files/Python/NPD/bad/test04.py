def test4_create_object():
    obj = [None, None]
    return obj

def test4_call_method():
    instance = test4_create_object()
    return instance[0].execute()

def test4_run_task():
    result = test4_call_method()
    return result

test4_run_task()