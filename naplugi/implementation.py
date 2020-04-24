import inspect
import sys
from typing import Callable, Optional, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .plugin import Plugin  # noqa: F401


class HookImpl:
    def __init__(
        self,
        function: Callable,
        plugin: Optional['Plugin'] = None,
        hookwrapper: bool = False,
        optionalhook: bool = False,
        tryfirst: bool = False,
        trylast: bool = False,
        specname: str = '',
        enabled: bool = True,
    ):
        self.function = function
        self.argnames, self.kwargnames = varnames(self.function)
        self._plugin = plugin
        self.hookwrapper = hookwrapper
        self.optionalhook = optionalhook
        self.tryfirst = tryfirst
        self.trylast = trylast
        self._specname = specname
        self.enabled = enabled

    @property
    def plugin(self) -> Any:
        return self._plugin.object if self._plugin else None

    @property
    def plugin_name(self) -> str:
        return self._plugin.name if self._plugin else 'None'

    @property
    def opts(self) -> dict:
        # legacy
        return {
            x: getattr(self, x)
            for x in [
                'hookwrapper',
                'optionalhook',
                'tryfirst',
                'trylast',
                'specname',
            ]
        }

    def __repr__(self) -> str:
        # these are all False by default
        truthy = [
            attr
            for attr in ('hookwrapper', 'optionalhook', 'tryfirst', 'trylast')
            if getattr(self, attr)
        ]
        suffix = (' ' + " ".join(truthy)) if truthy else ''
        return (
            f"<HookImpl plugin={self.plugin_name!r}"
            f" spec={self.specname!r}{suffix}>"
        )

    def __call__(self, *args):
        return self.function(*args)

    @property
    def specname(self) -> str:
        return self._specname or self.function.__name__


class HookSpec:
    def __init__(
        self,
        namespace: Any,
        name: str,
        *,
        firstresult: bool = False,
        historic: bool = False,
        warn_on_impl: Optional[Warning] = None,
    ):
        self.namespace = namespace
        self.name = name
        self.function = getattr(namespace, name)
        self.argnames, self.kwargnames = varnames(self.function)
        self.firstresult = firstresult
        self.historic = historic
        self.warn_on_impl = warn_on_impl

    @property
    def opts(self) -> dict:
        # legacy
        return {
            'firstresult': self.firstresult,
            'historic': self.historic,
            'warn_on_impl': self.warn_on_impl,
        }

    def __repr__(self) -> str:
        # these are all False by default
        truthy = [
            attr
            for attr in ('firstresult', 'historic', 'warn_on_impl')
            if getattr(self, attr)
        ]
        suffix = (' ' + " ".join(truthy)) if truthy else ''
        return f"<HookSpec {self.name!r} args={self.argnames!r}{suffix}>"


# TODO: can this be improved?
def varnames(func):
    """Return tuple of positional and keywrord argument names for a function,
    method, class or callable.

    In case of a class, its ``__init__`` method is considered.
    For methods the ``self`` parameter is not included.
    """
    cache = getattr(func, "__dict__", {})
    try:
        return cache["_varnames"]
    except KeyError:
        pass

    if inspect.isclass(func):
        try:
            func = func.__init__
        except AttributeError:
            return (), ()
    elif not inspect.isroutine(func):  # callable object?
        try:
            func = getattr(func, "__call__", func)
        except Exception:
            return (), ()

    try:  # func MUST be a function or method here or we won't parse any args
        spec = inspect.getfullargspec(func)
    except TypeError:
        return (), ()

    args, defaults = tuple(spec.args), spec.defaults
    if defaults:
        index = -len(defaults)
        args, kwargs = args[:index], tuple(args[index:])
    else:
        kwargs = ()

    # strip any implicit instance arg
    # pypy3 uses "obj" instead of "self" for default dunder methods
    _PYPY3 = hasattr(sys, "pypy_version_info") and sys.version_info.major == 3
    implicit_names = ("self",) if not _PYPY3 else ("self", "obj")
    if args:
        if inspect.ismethod(func) or (
            "." in getattr(func, "__qualname__", ())
            and args[0] in implicit_names
        ):
            args = args[1:]

    try:
        cache["_varnames"] = args, kwargs
    except TypeError:
        pass
    return args, kwargs
