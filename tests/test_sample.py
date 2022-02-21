from asyncit import Asyncit


def append_one(alist):
    alist.append(".")


def test_run():
    alist = []
    asyncit = Asyncit()
    for i in range(10):
        asyncit.run(append_one, alist)
    asyncit.wait()
    assert len(alist) == 10
