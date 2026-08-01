"""Plugin resolution for ``"package.module:Attr"`` specs.

Adapters, parsers, embedders, and reporters are supplied as plugin specs in
configuration (for example ``source.adapter``). This module resolves those
specs to Python objects with clear, actionable errors: a malformed spec,
failed import, missing attribute, or type mismatch each raise
:class:`~linkdiscovery.errors.PluginError` naming the spec.

:func:`load_plugin` returns the attribute exactly as found (a class stays a
class); :func:`instantiate_plugin` additionally calls a callable attribute
with no arguments, which is the common path for stage implementations that
take all parameters through their stage method.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from linkdiscovery.errors import PluginError

__all__ = ["instantiate_plugin", "load_plugin"]


def _split_spec(spec: str) -> tuple[str, str]:
    """Split a spec into (module, attribute), raising ``PluginError`` when malformed."""
    if not isinstance(spec, str) or spec.count(":") != 1:
        raise PluginError(
            f"invalid plugin spec {spec!r}; expected 'package.module:Attr' with exactly "
            "one ':' separating the module path from the attribute name"
        )
    module_name, _, attr_name = spec.partition(":")
    if not module_name or not attr_name:
        raise PluginError(
            f"invalid plugin spec {spec!r}; both the module path and the attribute name "
            "must be non-empty"
        )
    return module_name, attr_name


def _check_expected(obj: object, expected: type, spec: str) -> None:
    """Verify ``obj`` satisfies ``expected``, raising ``PluginError`` if not.

    Instances are checked with ``isinstance`` (which supports
    ``runtime_checkable`` Protocols). Classes are checked with ``issubclass``
    when the expected type supports it; data Protocols (those with non-method
    members) cannot be checked at class level, so classes are accepted and
    verified after instantiation instead.
    """
    if isinstance(obj, type):
        try:
            conforms = issubclass(obj, expected)
        except TypeError:
            return  # data Protocol: class-level check impossible; checked on instances
        if not conforms:
            raise PluginError(
                f"plugin {spec!r} resolved to class {obj.__qualname__}, which is not a "
                f"subclass of {expected.__name__}"
            )
        return
    if not _satisfies(obj, expected, spec):
        raise PluginError(
            f"plugin {spec!r} resolved to an instance of {type(obj).__name__}, which does "
            f"not satisfy {expected.__name__}"
        )


def _satisfies(obj: object, expected: type, spec: str) -> bool:
    """``isinstance`` with non-runtime-checkable Protocols reported as ``PluginError``."""
    try:
        return isinstance(obj, expected)
    except TypeError as exc:
        raise PluginError(
            f"cannot type-check plugin {spec!r} against {expected.__name__}: {exc}; "
            "expected types must be classes or @runtime_checkable Protocols"
        ) from exc


def load_plugin(spec: str, expected: type | None = None) -> Any:
    """Resolve ``"package.module:Attr"`` to the named attribute.

    The attribute is returned as-is: classes are not instantiated. When
    ``expected`` is given, instances are validated with ``isinstance`` and
    classes with ``issubclass`` where the expected type supports it. Raises
    ``PluginError`` on a malformed spec, import failure (with the original
    error chained), missing attribute, or type mismatch.
    """
    module_name, attr_name = _split_spec(spec)
    try:
        module = import_module(module_name)
    except ImportError as exc:
        raise PluginError(
            f"cannot import module {module_name!r} for plugin {spec!r}: {exc}; "
            "check that the package is installed and the module path is spelled correctly"
        ) from exc
    try:
        obj = getattr(module, attr_name)
    except AttributeError as exc:
        raise PluginError(
            f"module {module_name!r} has no attribute {attr_name!r} (from plugin {spec!r})"
        ) from exc
    if expected is not None:
        _check_expected(obj, expected, spec)
    return obj


def instantiate_plugin(spec: str, expected: type | None = None) -> Any:
    """Resolve a spec and return a ready instance.

    If the resolved attribute is a class, it is called with no arguments;
    otherwise the attribute itself is returned. When ``expected`` is given,
    the final instance is validated with ``isinstance`` (data Protocols are
    checkable here even when they are not at class level). Raises
    ``PluginError`` when resolution fails, zero-arg construction fails (with
    the original error chained), or the instance does not satisfy
    ``expected``.
    """
    obj = load_plugin(spec, expected)
    if isinstance(obj, type):
        try:
            obj = obj()
        except Exception as exc:
            raise PluginError(
                f"plugin {spec!r} could not be instantiated with no arguments: {exc}; "
                "provide a factory or an already-constructed instance instead"
            ) from exc
    if expected is not None and not _satisfies(obj, expected, spec):
        raise PluginError(
            f"plugin {spec!r} produced an instance of {type(obj).__name__}, which does "
            f"not satisfy {expected.__name__}"
        )
    return obj
