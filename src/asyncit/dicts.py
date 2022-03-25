class DotDictMeta(type):
    def __repr__(cls):
        return cls.__name__


class DotDict(dict, metaclass=DotDictMeta):
    """Dictionary that supports dot notation as well as dictionary access notation.
    Use the dot motation only for get values, not for setting.

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

    def __setitem__(self, *args, **kwargs):
        new_args = [args[0], args[1]]
        if isinstance(new_args[1], dict):
            new_args[1] = DotDict(new_args[1])
        return super().__setitem__(*new_args, **kwargs)

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
