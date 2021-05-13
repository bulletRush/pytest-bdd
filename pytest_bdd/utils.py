"""Various utility functions."""
import os
import importlib
import sys
from sys import _getframe
from inspect import getframeinfo

import six

CONFIG_STACK = []

if six.PY2:
    from inspect import getargspec as _getargspec

    def get_args(func):
        """Get a list of argument names for a function.

        :param func: The function to inspect.

        :return: A list of argument names.
        :rtype: list
        """
        return _getargspec(func).args

    def get_args_default_values(func):
        d = {}
        spec = _getargspec(func)
        if spec.defaults:
            for idx, arg in enumerate(spec.args[-len(spec.defaults):]):
                d[arg] = spec.defaults[idx]
        return d

else:
    from inspect import signature as _signature

    def get_args(func):
        """Get a list of argument names for a function.

        :param func: The function to inspect.

        :return: A list of argument names.
        :rtype: list
        """
        params = _signature(func).parameters.values()
        return [param.name for param in params if param.kind == param.POSITIONAL_OR_KEYWORD]

    def get_args_default_values(func):
        params = _signature(func).parameters.values()
        d = {}
        for param in params:
            if param.kind != param.POSITIONAL_OR_KEYWORD:
                continue
            if param.default == param.empty:
                continue
            d[param.name] = param.default
        return d


def get_parametrize_markers_args(node):
    """In pytest 3.6 new API to access markers has been introduced and it deprecated
    MarkInfo objects.

    This function uses that API if it is available otherwise it uses MarkInfo objects.
    """
    return tuple(arg for mark in node.iter_markers("parametrize") for arg in mark.args)


def get_caller_module_locals(depth=2):
    """Get the caller module locals dictionary.

    We use sys._getframe instead of inspect.stack(0) because the latter is way slower, since it iterates over
    all the frames in the stack.
    """
    return _getframe(depth).f_locals


def get_caller_module_path(depth=2):
    """Get the caller module path.

    We use sys._getframe instead of inspect.stack(0) because the latter is way slower, since it iterates over
    all the frames in the stack.
    """
    frame = _getframe(depth)
    return getframeinfo(frame, context=0).filename


def iter_modules(path):
    r_path = os.path.normpath(os.path.abspath(path))
    while r_path not in sys.path:
        p_path = os.path.normpath(os.path.join(r_path, os.pardir))
        if p_path == r_path:
            break
        r_path = p_path

    if r_path not in sys.path:
        sys.path.append(r_path)

    for root, sub_dir_l, file_l in os.walk(path):
        for f in file_l:
            if not f.endswith(".py") or f.startswith("__") or f.startswith(
                    "_"):
                continue
            interface_name = f[:-3]
            module_path = os.path.relpath(root, r_path).split("/")
            module_path.append(interface_name)
            module_path = ".".join(module_path)
            module = importlib.import_module(module_path)
            yield module_path, module
