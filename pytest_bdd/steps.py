"""Step decorators.

Example:

@given("I have an article", target_fixture="article")
def given_article(author):
    return create_test_article(author=author)


@when("I go to the article page")
def go_to_the_article_page(browser, article):
    browser.visit(urljoin(browser.url, "/articles/{0}/".format(article.id)))


@then("I should not see the error message")
def no_error_message(browser):
    with pytest.raises(ElementDoesNotExist):
        browser.find_by_css(".message.error").first


Multiple names for the steps:

@given("I have an article")
@given("there is an article")
def article(author):
    return create_test_article(author=author)


Reusing existing fixtures for a different step name:


@given("I have a beautiful article")
def given_beautiful_article(article):
    pass

"""

from __future__ import absolute_import
import inspect
import sys
import pytest

try:
    from _pytest import fixtures as pytest_fixtures
except ImportError:
    from _pytest import python as pytest_fixtures

from .feature import force_encode
from .types import GIVEN, WHEN, THEN
from .parsers import get_parser
from .utils import get_args, get_caller_module_locals


def get_step_fixture_name(name, type_, encoding=None):
    """Get step fixture name.

    :param name: unicode string
    :param type: step type
    :param encoding: encoding
    :return: step fixture name
    :rtype: string
    """
    return "pytestbdd_{type}_{name}".format(
        type=type_, name=force_encode(name, **(dict(encoding=encoding) if encoding else {}))
    )


def given(name, converters=None, target_fixture=None, **kwargs):
    """Given step decorator.

    :param name: Step name or a parser object.
    :param converters: Optional `dict` of the argument or parameter converters in form
                       {<param_name>: <converter function>}.
    :param target_fixture: Target fixture name to replace by steps definition function
    :param kwargs: default value
    :return: Decorator function for the step.
    """
    return _step_decorator(GIVEN, name, converters=converters, target_fixture=target_fixture, extra_args=kwargs)


def when(name, converters=None, target_fixture=None, **kwargs):
    """When step decorator.

    :param name: Step name or a parser object.
    :param converters: Optional `dict` of the argument or parameter converters in form
                       {<param_name>: <converter function>}.
    :param target_fixture: Target fixture name to replace by steps definition function

    :return: Decorator function for the step.
    """
    return _step_decorator(WHEN, name, converters=converters, target_fixture=target_fixture, extra_args=kwargs)


def then(name, converters=None, target_fixture=None, **kwargs):
    """Then step decorator.

    :param name: Step name or a parser object.
    :param converters: Optional `dict` of the argument or parameter converters in form
                       {<param_name>: <converter function>}.
    :param target_fixture: Target fixture name to replace by steps definition function

    :return: Decorator function for the step.
    """
    return _step_decorator(THEN, name, converters=converters, target_fixture=target_fixture, extra_args=kwargs)


def _step_decorator(step_type, step_name, converters=None, target_fixture=None, extra_args=None):
    """Step decorator for the type and the name.

    :param str step_type: Step type (GIVEN, WHEN or THEN).
    :param str step_name: Step name as in the feature file.
    :param dict converters: Optional step arguments converters mapping
    :param target_fixture: Optional fixture name to replace by step definition
    :param extra_args: extra args
    :return: Decorator function for the step.
    """

    def decorator(func):
        func_name = getattr(func, "origin_name", getattr(func, "__name__"))
        step_func = func
        parser_instance = get_parser(step_name)
        parsed_step_name = parser_instance.name

        step_func.__name__ = force_encode(parsed_step_name)

        def lazy_step_func():
            return step_func

        step_func.step_type = step_type
        lazy_step_func.step_type = step_type

        # Preserve the docstring
        lazy_step_func.__doc__ = func.__doc__

        step_func.parser = lazy_step_func.parser = parser_instance
        if converters:
            step_func.converters = lazy_step_func.converters = converters

        step_func.target_fixture = lazy_step_func.target_fixture = target_fixture
        step_func.origin_name = lazy_step_func.origin_name = func_name

        fixture_step_name = get_step_fixture_name(parsed_step_name, step_type)

        if extra_args:
            extra_args_map = getattr(step_func, "extra_args_map", {})
            if not extra_args_map:
                step_func.extra_args_map = {}
            step_func.extra_args_map[fixture_step_name] = extra_args

        lazy_step_func = pytest.fixture()(lazy_step_func)

        caller_locals = get_caller_module_locals()
        caller_locals[fixture_step_name] = lazy_step_func
        return func

    return decorator


def pytest_fixture_setup(fixturedef, request):
    """ Execution of fixture setup. """
    kwargs = {}
    for argname in fixturedef.argnames:
        fixdef = request._get_active_fixturedef(argname)
        result, arg_cache_key, exc = fixdef.cached_result
        request._check_scope(argname, request.scope, fixdef.scope)
        kwargs[argname] = result

    fixturefunc = pytest_fixtures.resolve_fixture_function(fixturedef, request)
    my_cache_key = 0
    try:
        result = pytest_fixtures.call_fixture_func(fixturefunc, request, kwargs)
    except pytest_fixtures.TEST_OUTCOME:
        fixturedef.cached_result = (None, my_cache_key, sys.exc_info())
        raise
    fixturedef.cached_result = (result, my_cache_key, None)
    return result


def inject_fixture(request, arg, value, inject_func=False):
    """Inject fixture into pytest fixture request.

    :param request: pytest fixture request
    :param arg: argument name
    :param value: argument value
    """
    fd_kwargs = {
        "fixturemanager": request._fixturemanager,
        "baseid": None,
        "argname": arg,
        "scope": "function",
        "params": None,
    }
    if inject_func:
        fd_kwargs["func"] = value
    else:
        fd_kwargs["func"] = lambda: value

    if "yieldctx" in get_args(pytest_fixtures.FixtureDef.__init__):
        fd_kwargs["yieldctx"] = False

    fd = pytest_fixtures.FixtureDef(**fd_kwargs)
    if inject_func:
        pytest_fixture_setup(fd, request)
    else:
        fd.cached_result = (value, 0, None)

    old_fd = request._fixture_defs.get(arg)
    add_fixturename = arg not in request.fixturenames

    def fin():
        request._fixturemanager._arg2fixturedefs[arg].remove(fd)
        request._fixture_defs[arg] = old_fd

        if add_fixturename:
            request._pyfuncitem._fixtureinfo.names_closure.remove(arg)

    request.addfinalizer(fin)

    # inject fixture definition
    request._fixturemanager._arg2fixturedefs.setdefault(arg, []).insert(0, fd)
    # inject fixture value in request cache
    request._fixture_defs[arg] = fd
    if add_fixturename:
        request._pyfuncitem._fixtureinfo.names_closure.append(arg)
