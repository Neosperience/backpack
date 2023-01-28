''' Utilities for AWS Panorama application development. '''

__version__ = '0.2.2'
__author__ = 'Janos Tolgyesi'

import functools

def lazy_property(func):
    ''' Caches the return value of a function, and turns it into a property.

    Intended to be used as a function decorator::

        >>> class Foo:
        >>>     @lazy_property
        >>>     def bar(self):
        >>>         print('expensive calculation')
        >>>         return 'bar'
        >>> foo = Foo()
        >>> foo.bar()
        expensive calculation
        'bar'
        >>> foo.bar()
        'bar'
    '''
    attrib_name = '_' + func.__name__
    @property
    @functools.wraps(func)
    def lazy_wrapper(instance, *args, **kwargs):
        if hasattr(instance, attrib_name):
            return getattr(instance, attrib_name)
        value = func(instance, *args, **kwargs)
        object.__setattr__(instance, attrib_name, value)
        return value
    return lazy_wrapper
