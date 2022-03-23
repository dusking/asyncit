import pytest

from asyncit import Asyncit
from asyncit.dicts import DotDict


def append_one(alist):
    alist.append(".")


def test_asyncit_run():
    alist = []
    asyncit = Asyncit()
    for _ in range(10):
        asyncit.run(append_one, alist)
    asyncit.wait()
    assert len(alist) == 10


def test_dotdict_basic():
    dotdict_1 = DotDict(a="a", b="")
    assert dotdict_1.a == "a"
    assert dotdict_1.b == ""


def test_dotdict_update():
    dotdict_1 = DotDict({"a": "A"})
    dotdict_1.update({"b": "B"})
    dotdict_1.update(c="C")
    dotdict_1.update(DotDict(d="D"))
    data = dotdict_1.update(dict(e="E"))
    assert len(dotdict_1) == len(data) == 5


def test_dotdict_set():
    dotdict = DotDict({"a": "A"})
    assert dotdict.a == "A"
    dotdict = DotDict(a="A")
    assert dotdict.a == "A"
    dotdict = DotDict()
    dotdict.a = "A"
    assert dotdict.a == "A"
    dotdict = DotDict()
    dotdict["a"] = "A"
    assert dotdict.a == "A"

def test_dotdict_get():
    dotdict_1 = DotDict({"a": "A"})
    assert dotdict_1.a == "A"
    assert dotdict_1["a"] == "A"
    assert dotdict_1.get("a") == "A"
    assert dotdict_1.b is None
    assert dotdict_1.get("b") is None
    with pytest.raises(KeyError):
        _ = dotdict_1["b"]
    dotdict_1.c = {"c": "C"}
    assert dotdict_1.c.c == "C"
