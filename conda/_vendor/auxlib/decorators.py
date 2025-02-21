from __future__ import absolute_import, division, print_function
from ._vendor.collections_patch import Hashable
from types import GeneratorType

from .compat import wraps

# TODO: spend time filling out functionality and make these more robust


def memoize(func):
    """
    Decorator to cause a function to cache it's results for each combination of
    inputs and return the cached result on subsequent calls.  Does not support
    named arguments or arg values that are not hashable.

    >>> @memoize
    ... def foo(x):
    ...     print('running function with', x)
    ...     return x+3
    ...
    >>> foo(10)
    running function with 10
    13
    >>> foo(10)
    13
    >>> foo(11)
    running function with 11
    14
    >>> @memoize
    ... def range_tuple(limit):
    ...     print('running function')
    ...     return tuple(i for i in range(limit))
    ...
    >>> range_tuple(3)
    running function
    (0, 1, 2)
    >>> range_tuple(3)
    (0, 1, 2)
    >>> @memoize
    ... def range_iter(limit):
    ...     print('running function')
    ...     return (i for i in range(limit))
    ...
    >>> range_iter(3)
    Traceback (most recent call last):
    TypeError: Can't memoize a generator or non-hashable object!
    """
    func._result_cache = {}  # pylint: disable-msg=W0212

    @wraps(func)
    def _memoized_func(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        if key in func._result_cache:  # pylint: disable-msg=W0212
            return func._result_cache[key]  # pylint: disable-msg=W0212
        else:
            result = func(*args, **kwargs)
            if isinstance(result, GeneratorType) or not isinstance(result, Hashable):
                raise TypeError("Can't memoize a generator or non-hashable object!")
            func._result_cache[key] = result  # pylint: disable-msg=W0212
            return result

    return _memoized_func


def memoizemethod(method):
    """
    Decorator to cause a method to cache it's results in self for each
    combination of inputs and return the cached result on subsequent calls.
    Does not support named arguments or arg values that are not hashable.

    >>> class Foo (object):
    ...   @memoizemethod
    ...   def foo(self, x, y=0):
    ...     print('running method with', x, y)
    ...     return x + y + 3
    ...
    >>> foo1 = Foo()
    >>> foo2 = Foo()
    >>> foo1.foo(10)
    running method with 10 0
    13
    >>> foo1.foo(10)
    13
    >>> foo2.foo(11, y=7)
    running method with 11 7
    21
    >>> foo2.foo(11)
    running method with 11 0
    14
    >>> foo2.foo(11, y=7)
    21
    >>> class Foo (object):
    ...   def __init__(self, lower):
    ...     self.lower = lower
    ...   @memoizemethod
    ...   def range_tuple(self, upper):
    ...     print('running function')
    ...     return tuple(i for i in range(self.lower, upper))
    ...   @memoizemethod
    ...   def range_iter(self, upper):
    ...     print('running function')
    ...     return (i for i in range(self.lower, upper))
    ...
    >>> foo = Foo(3)
    >>> foo.range_tuple(6)
    running function
    (3, 4, 5)
    >>> foo.range_tuple(7)
    running function
    (3, 4, 5, 6)
    >>> foo.range_tuple(6)
    (3, 4, 5)
    >>> foo.range_iter(6)
    Traceback (most recent call last):
    TypeError: Can't memoize a generator or non-hashable object!
    """

    @wraps(method)
    def _wrapper(self, *args, **kwargs):
        # NOTE:  a __dict__ check is performed here rather than using the
        # built-in hasattr function because hasattr will look up to an object's
        # class if the attr is not directly found in the object's dict.  That's
        # bad for this if the class itself has a memoized classmethod for
        # example that has been called before the memoized instance method,
        # then the instance method will use the class's result cache, causing
        # its results to be globally stored rather than on a per instance
        # basis.
        if '_memoized_results' not in self.__dict__:
            self._memoized_results = {}
        memoized_results = self._memoized_results

        key = (method.__name__, args, tuple(sorted(kwargs.items())))
        if key in memoized_results:
            return memoized_results[key]
        else:
            try:
                result = method(self, *args, **kwargs)
            except KeyError as e:
                if '__wrapped__' in str(e):
                    result = None  # is this the right thing to do?  happened during py3 conversion
                else:
                    raise
            if isinstance(result, GeneratorType) or not isinstance(result, Hashable):
                raise TypeError("Can't memoize a generator or non-hashable object!")
            return memoized_results.setdefault(key, result)

    return _wrapper


# class memoizemethod(object):
#     """cache the return value of a method
#
#     This class is meant to be used as a decorator of methods. The return value
#     from a given method invocation will be cached on the instance whose method
#     was invoked. All arguments passed to a method decorated with memoize must
#     be hashable.
#
#     If a memoized method is invoked directly on its class the result will not
#     be cached. Instead the method will be invoked like a static method:
#     class Obj(object):
#         @memoize
#         def add_to(self, arg):
#             return self + arg
#     Obj.add_to(1) # not enough arguments
#     Obj.add_to(1, 2) # returns 3, result is not cached
#     """
#     def __init__(self, func):
#         self.func = func
#     def __get__(self, obj, objtype=None):
#         if obj is None:
#             return self.func
#         return partial(self, obj)
#     def __call__(self, *args, **kw):
#         obj = args[0]
#         try:
#             cache = obj.__cache
#         except AttributeError:
#             cache = obj.__cache = {}
#         key = (self.func, args[1:], frozenset(kw.items()))
#         try:
#             res = cache[key]
#         except KeyError:
#             res = cache[key] = self.func(*args, **kw)
#         return res


def clear_memoized_methods(obj, *method_names):
    """
    Clear the memoized method or @memoizeproperty results for the given
    method names from the given object.

    >>> v = [0]
    >>> def inc():
    ...     v[0] += 1
    ...     return v[0]
    ...
    >>> class Foo(object):
    ...    @memoizemethod
    ...    def foo(self):
    ...        return inc()
    ...    @memoizeproperty
    ...    def g(self):
    ...       return inc()
    ...
    >>> f = Foo()
    >>> f.foo(), f.foo()
    (1, 1)
    >>> clear_memoized_methods(f, 'foo')
    >>> (f.foo(), f.foo(), f.g, f.g)
    (2, 2, 3, 3)
    >>> (f.foo(), f.foo(), f.g, f.g)
    (2, 2, 3, 3)
    >>> clear_memoized_methods(f, 'g', 'no_problem_if_undefined')
    >>> f.g, f.foo(), f.g
    (4, 2, 4)
    >>> f.foo()
    2
    """
    for key in list(getattr(obj, '_memoized_results', {}).keys()):
        # key[0] is the method name
        if key[0] in method_names:
            del obj._memoized_results[key]

    property_dict = obj._cache_
    for prop in method_names:
        inner_attname = '__%s' % prop
        if inner_attname in property_dict:
            del property_dict[inner_attname]


def memoizedproperty(func):
    """
    Decorator to cause a method to cache it's results in self for each
    combination of inputs and return the cached result on subsequent calls.
    Does not support named arguments or arg values that are not hashable.

    >>> class Foo (object):
    ...   _x = 1
    ...   @memoizedproperty
    ...   def foo(self):
    ...     self._x += 1
    ...     print('updating and returning {0}'.format(self._x))
    ...     return self._x
    ...
    >>> foo1 = Foo()
    >>> foo2 = Foo()
    >>> foo1.foo
    updating and returning 2
    2
    >>> foo1.foo
    2
    >>> foo2.foo
    updating and returning 2
    2
    >>> foo1.foo
    2
    """
    inner_attname = '__%s' % func.__name__

    def new_fget(self):
        if not hasattr(self, '_cache_'):
            self._cache_ = dict()
        cache = self._cache_
        if inner_attname not in cache:
            cache[inner_attname] = func(self)
        return cache[inner_attname]

    return property(new_fget)


# def memoized_property(fget):
#     """
#     Return a property attribute for new-style classes that only calls its getter on the first
#     access. The result is stored and on subsequent accesses is returned, preventing the need to
#     call the getter any more.
#     Example::
#         >>> class C(object):
#         ...     load_name_count = 0
#         ...     @memoized_property
#         ...     def name(self):
#         ...         "name's docstring"
#         ...         self.load_name_count += 1
#         ...         return "the name"
#         >>> c = C()
#         >>> c.load_name_count
#         0
#         >>> c.name
#         "the name"
#         >>> c.load_name_count
#         1
#         >>> c.name
#         "the name"
#         >>> c.load_name_count
#         1
#     """
#     attr_name = '_{0}'.format(fget.__name__)
#
#     @wraps(fget)
#     def fget_memoized(self):
#         if not hasattr(self, attr_name):
#             setattr(self, attr_name, fget(self))
#         return getattr(self, attr_name)
#
#     return property(fget_memoized)

class classproperty(object):  # pylint: disable=C0103
    # from celery.five

    def __init__(self, getter=None, setter=None):
        if getter is not None and not isinstance(getter, classmethod):
            getter = classmethod(getter)
        if setter is not None and not isinstance(setter, classmethod):
            setter = classmethod(setter)
        self.__get = getter
        self.__set = setter

        info = getter.__get__(object)  # just need the info attrs.
        self.__doc__ = info.__doc__
        self.__name__ = info.__name__
        self.__module__ = info.__module__

    def __get__(self, obj, type_=None):
        if obj and type_ is None:
            type_ = obj.__class__
        return self.__get.__get__(obj, type_)()

    def __set__(self, obj, value):
        if obj is None:
            return self
        return self.__set.__get__(obj)(value)

    def setter(self, setter):
        return self.__class__(self.__get, setter)

# memoize & clear:
#     class method
#     function
#     classproperty
#     property
#     staticproperty?
# memoizefunction
# memoizemethod
# memoizeproperty
#
#
