class DotDictMeta(type):
    def __repr__(cls):
        return cls.__name__


class DotDict(dict, metaclass=DotDictMeta):
    """Dictionary that supports dot notation as well as dictionary access notation.

    usage:
    >>> d1 = DotDict()
    >>> d['val2'] = 'second'
    >>> print(d.val2)
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
