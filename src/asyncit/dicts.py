import re
from collections import OrderedDict
from collections.abc import Mapping


class RecursiveNone:
    """
    dummy object. enable access object attributes and still get None
    """

    def __str__(self):
        return ""

    def __repr__(self):
        return ""

    def __getattr__(self, key):
        return RecursiveNone()


class DotDict(dict):
    """
    a dictionary that supports dot notation
    as well as dictionary access notation
    usage: d = DotDict() or d = DotDict({'val1':'first'})
    set attributes: d.val2 = 'second' or d['val2'] = 'second'
    get attributes: d.val2 or d['val2']
    """

    # __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, dct, case_insensitive=False):
        super().__init__()
        for key, value in dct.items():
            if isinstance(value, dict):
                value = DotDict(value)
            if case_insensitive:
                key = self.to_lower_snake(key)
            self[key] = value

    def __getattr__(self, k):
        try:
            return self.get(k, self.get(self.to_lower_snake(k)))
        except KeyError as ex:
            return None

    def to_lower_snake(self, value):
        if "_" not in value and value != value.upper():
            pattern = re.compile(r"(?<!^)(?=[A-Z])")
            value = pattern.sub("_", value).lower()
        return value.lower()


class OrderedDotDict(OrderedDict):
    """
    Quick and dirty implementation of a dot-able dict, which allows access and
    assignment via object properties rather than dict indexing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        # we could just call super(DotDict, self).__init__(*args, **kwargs)
        # but that won't get us nested dotdict objects
        od = OrderedDict(*args, **kwargs)
        for key, val in od.items():
            if isinstance(val, Mapping):
                value = DotDict(val)
            else:
                value = val
            self[key] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError as ex:
            raise AttributeError(f"No attribute called: {name}") from ex

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError as ex:
            raise AttributeError(f"No attribute called: {k}") from ex

    __setattr__ = OrderedDict.__setitem__


class CaseInsensitiveDict(dict):

    """Basic case insensitive dict with strings only keys."""

    proxy = {}

    def __init__(self, data):
        super().__init__()
        self.proxy = dict((k.lower(), k) for k in data)
        for k in data:
            self[k] = data[k]

    def __contains__(self, k):
        return k.lower() in self.proxy

    def __delitem__(self, k):
        key = self.proxy[k.lower()]
        super().__delitem__(key)
        del self.proxy[k.lower()]

    def __getitem__(self, k):
        key = self.proxy[k.lower()]
        return super().__getitem__(key)

    def get(self, k, default=None):
        return self[k] if k in self else default

    def __setitem__(self, k, v):
        super().__setitem__(k, v)
        self.proxy[k.lower()] = k

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        for k in dict(*args, **kwargs):
            self.proxy[k.lower()] = k
