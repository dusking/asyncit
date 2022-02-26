import re
from itertools import chain
from collections import OrderedDict
from collections.abc import Mapping

str_base = str, bytes, bytearray
items = "items"

_RaiseKeyError = object()  # singleton for no-default behavior


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


class DotDictMeta(type):
    def __repr__(cls):
        return cls.__name__


class DotDict(dict, metaclass=DotDictMeta):
    """
    a dictionary that supports dot notation
    as well as dictionary access notation
    usage: d = DotDict() or d = DotDict({'val1':'first'})
    set attributes: d.val2 = 'second' or d['val2'] = 'second'
    get attributes: d.val2 or d['val2']
    """

    __slots__ = ()
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getattr__(self, k):
        """Get property"""
        value = self.get(k)
        if isinstance(value, dict):
            return DotDict(value)
        return value

    def __getitem__(self, k):
        """Indexing operator"""
        if k not in self:
            raise KeyError(k)
        value = self.get(k)
        if isinstance(value, dict):
            return DotDict(value)
        return value

    def get(self, k, default=None):
        value = super().get(k, default)
        if isinstance(value, dict):
            return DotDict(value)
        return value

    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)
        return self

    def copy(self):  # don't delegate w/ super - dict.copy() -> dict :(
        return type(self)(self)


class DotDictV1(dict):
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


class CaseInsensitiveDictV2(dict):
    __slots__ = ()
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def process_args(self, mapping=(), **kwargs):
        if hasattr(mapping, items):
            mapping = getattr(mapping, items)()
        return ((self.ensure_lower(k), v) for k, v in chain(mapping, getattr(kwargs, items)()))

    @classmethod
    def ensure_lower(cls, maybe_str):
        """dict keys can be any hashable object - only call lower if str"""
        return maybe_str.lower() if isinstance(maybe_str, str_base) else maybe_str

    def __init__(self, mapping=(), **kwargs):
        super().__init__(self.process_args(mapping, **kwargs))
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = CaseInsensitiveDictV2(value)

    def __getitem__(self, k):
        return super().__getitem__(self.ensure_lower(k))

    def __setitem__(self, k, v):
        return super().__setitem__(self.ensure_lower(k), v)

    def __delitem__(self, k):
        return super().__delitem__(self.ensure_lower(k))

    def __getattr__(self, k):
        value = self.get(k)
        if isinstance(value, dict):
            return CaseInsensitiveDictV2(value)
        return value

    def get(self, k, default=None):
        return super().get(self.ensure_lower(k), default)

    def setdefault(self, k, default=None):
        return super().setdefault(self.ensure_lower(k), default)

    def pop(self, k, v=_RaiseKeyError):
        if v is _RaiseKeyError:
            return super().pop(self.ensure_lower(k))
        return super().pop(self.ensure_lower(k), v)

    def update(self, mapping=(), **kwargs):
        super().update(self.process_args(mapping, **kwargs))
        return self

    def __contains__(self, k):
        return super().__contains__(self.ensure_lower(k))

    def copy(self):  # don't delegate w/ super - dict.copy() -> dict :(
        return type(self)(self)

    @classmethod
    def fromkeys(cls, keys, value=None):
        return super().fromkeys((cls.ensure_lower(k) for k in keys), value)

    # def __repr__(self):
    #     return '{0}({1})'.format(type(self).__name__, super().__repr__())
