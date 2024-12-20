"""Scenario implementation.

The pytest will collect the test case and the steps will be executed
line by line.

Example:

test_publish_article = scenario(
    feature_name="publish_article.feature",
    scenario_name="Publishing the article",
)
"""
import collections
import os
import re

import pytest

try:
    from _pytest import fixtures as pytest_fixtures
except ImportError:
    from _pytest import python as pytest_fixtures

from . import exceptions
from .feature import force_unicode, get_feature, get_features
from .steps import get_step_fixture_name, inject_fixture
from .utils import CONFIG_STACK, get_args, get_caller_module_locals, get_caller_module_path, get_args_default_values, iter_modules

PYTHON_REPLACE_REGEX = re.compile(r"\W")
ALPHA_REGEX = re.compile(r"^\d+_*")
GENERAL_STEP_DEFS = None

# We have to keep track of the invocation of @scenario() so that we can reorder test item accordingly.
# In python 3.6+ this is no longer necessary, as the order is automatically retained.
_py2_scenario_creation_counter = 0


def find_argumented_step_fixture_name(name, type_, fixturemanager, request=None):
    """Find argumented step fixture name."""
    # happens to be that _arg2fixturedefs is changed during the iteration so we use a copy
    for fixturename, fixturedefs in list(fixturemanager._arg2fixturedefs.items()):
        for fixturedef in fixturedefs:
            parser = getattr(fixturedef.func, "parser", None)
            match = parser.is_matching(name) if parser else None
            if match:
                converters = getattr(fixturedef.func, "converters", {})
                for arg, value in parser.parse_arguments(name).items():
                    if arg in converters:
                        value = converters[arg](value)
                    if request:
                        inject_fixture(request, arg, value)
                parser_name = get_step_fixture_name(parser.name, type_)
                if request:
                    try:
                        request.getfixturevalue(parser_name)
                    except pytest_fixtures.FixtureLookupError:
                        continue
                return parser_name


def get_general_step_defs():
    global GENERAL_STEP_DEFS
    if GENERAL_STEP_DEFS is not None:
        return GENERAL_STEP_DEFS

    path = get_steps_def_dir()
    GENERAL_STEP_DEFS = {}
    if not os.path.exists(path):
        return GENERAL_STEP_DEFS
    for module_path, module in iter_modules(path):  # type: str,module
        for k, func in module.__dict__.items():
            if not k.startswith("pytestbdd_"):
                continue
            if k in GENERAL_STEP_DEFS:
                raise Exception("duplicated step defs: {0}".format(k))
            GENERAL_STEP_DEFS[k] = func
    return GENERAL_STEP_DEFS


def _find_general_step_function(request, step, scenario, encoding):
    general_step_defs = get_general_step_defs()
    if not general_step_defs:
        raise pytest_fixtures.FixtureLookupError(step.name, request)
    step_name = get_step_fixture_name(step.name, step.type, encoding)
    lazy_step_func = general_step_defs.get(step_name)
    if lazy_step_func is None:
        raise pytest_fixtures.FixtureLookupError(step.name, request)
    inject_fixture(
        request, step_name, lazy_step_func.__pytest_wrapped__.obj, inject_func=True)
    return request.getfixturevalue(get_step_fixture_name(step.name, step.type, encoding))


def _find_step_function(request, step, scenario, encoding):
    """Match the step defined by the regular expression pattern.

    :param request: PyTest request object.
    :param step: Step.
    :param scenario: Scenario.

    :return: Function of the step.
    :rtype: function
    """
    name = step.name
    try:
        # Simple case where no parser is used for the step
        return request.getfixturevalue(get_step_fixture_name(name, step.type, encoding))
    except pytest_fixtures.FixtureLookupError:
        try:
            # Could not find a fixture with the same name, let's see if there is a parser involved
            name = find_argumented_step_fixture_name(name, step.type, request._fixturemanager, request)
            if name:
                return request.getfixturevalue(name)
            return _find_general_step_function(request, step, scenario, encoding)
        except pytest_fixtures.FixtureLookupError:
            raise exceptions.StepDefinitionNotFoundError(
                u"""Step definition is not found: {step}."""
                """ Line {step.line_number} in scenario "{scenario.name}" in the feature "{feature.filename}""".format(
                    step=step, scenario=scenario, feature=scenario.feature
                )
            )


def _execute_step_function(request, scenario, step, step_func):
    """Execute step function.

    :param request: PyTest request.
    :param scenario: Scenario.
    :param Step step: Step.
    :param function step_func: Step function.
    :param example: Example table.
    """
    kw = dict(request=request, feature=scenario.feature, scenario=scenario, step=step, step_func=step_func)

    request.config.hook.pytest_bdd_before_step(**kw)

    kw["step_func_args"] = {}
    try:
        # Get the step argument values.
        args = get_args(step_func)
        default_values = get_args_default_values(step_func)
        kwargs = {}

        extra_args_map = getattr(step_func, "extra_args_map", {})
        if extra_args_map:
            extra_args = extra_args_map.get(get_step_fixture_name(step.name, step.type), {})
        else:
            extra_args = {}

        for arg in args:
            if arg in step.constant_params:
                # constant step params
                v = step.constant_params[arg]
                if v == step.SKIP_MARK:
                    continue
                kwargs[arg] = v
            elif arg in step.alias_params:
                # step params alias
                kwargs[arg] = step.alias_convert[arg](request)
            elif arg in extra_args:
                kwargs[arg] = extra_args[arg]
            else:
                try:
                    kwargs[arg] = request.getfixturevalue(arg)
                except pytest_fixtures.FixtureLookupError as e:
                    if arg in default_values:
                        kwargs[arg] = default_values[arg]
                    else:
                        raise
        kw["step_func_args"] = kwargs

        request.config.hook.pytest_bdd_before_step_call(**kw)
        target_fixture = getattr(step_func, "target_fixture", None)
        # Execute the step.
        return_value = step_func(**kwargs)
        if target_fixture:
            inject_fixture(request, target_fixture, return_value)

        request.config.hook.pytest_bdd_after_step(**kw)
    except Exception as exception:
        request.config.hook.pytest_bdd_step_error(exception=exception, **kw)
        raise


def _execute_scenario(feature, scenario, request, encoding):
    """Execute the scenario.

    :param feature: Feature.
    :param scenario: Scenario.
    :param request: request.
    :param encoding: Encoding.
    """
    request.config.hook.pytest_bdd_before_scenario(request=request, feature=feature, scenario=scenario)

    try:
        # Execute scenario steps
        for step in scenario.steps:
            try:
                step_func = _find_step_function(request, step, scenario, encoding=encoding)
            except exceptions.StepDefinitionNotFoundError as exception:
                request.config.hook.pytest_bdd_step_func_lookup_error(
                    request=request, feature=feature, scenario=scenario, step=step, exception=exception
                )
                raise
            _execute_step_function(request, scenario, step, step_func)
    finally:
        request.config.hook.pytest_bdd_after_scenario(request=request, feature=feature, scenario=scenario)


FakeRequest = collections.namedtuple("FakeRequest", ["module"])


def _get_scenario_decorator(feature, feature_name, scenario, scenario_name, encoding):
    global _py2_scenario_creation_counter

    counter = _py2_scenario_creation_counter
    _py2_scenario_creation_counter += 1

    # HACK: Ideally we would use `def decorator(fn)`, but we want to return a custom exception
    # when the decorator is misused.
    # Pytest inspect the signature to determine the required fixtures, and in that case it would look
    # for a fixture called "fn" that doesn't exist (if it exists then it's even worse).
    # It will error with a "fixture 'fn' not found" message instead.
    # We can avoid this hack by using a pytest hook and check for misuse instead.
    def decorator(*args):
        if not args:
            raise exceptions.ScenarioIsDecoratorOnly(
                "scenario function can only be used as a decorator. Refer to the documentation."
            )
        [fn] = args
        args = get_args(fn)
        function_args = list(args)
        for arg in scenario.get_example_params():
            if arg not in function_args:
                function_args.append(arg)

        @pytest.mark.usefixtures(*function_args)
        def scenario_wrapper(request):
            _execute_scenario(feature, scenario, request, encoding)
            return fn(*[request.getfixturevalue(arg) for arg in args])

        for param_set in scenario.get_params():
            if param_set:
                scenario_wrapper = pytest.mark.parametrize(*param_set)(scenario_wrapper)
        for tag in scenario.tags.union(feature.tags):
            config = CONFIG_STACK[-1]
            config.hook.pytest_bdd_apply_tag(tag=tag, function=scenario_wrapper)

        scenario_wrapper.__doc__ = u"{feature_name}: {scenario_name}".format(
            feature_name=feature_name, scenario_name=scenario_name
        )
        scenario_wrapper.__scenario__ = scenario
        scenario_wrapper.__pytest_bdd_counter__ = counter
        scenario.test_function = scenario_wrapper
        return scenario_wrapper

    return decorator


def scenario(feature_name, scenario_name, encoding="utf-8", example_converters=None, features_base_dir=None):
    """Scenario decorator.

    :param str feature_name: Feature file name. Absolute or relative to the configured feature base path.
    :param str scenario_name: Scenario name.
    :param str encoding: Feature file encoding.
    :param dict example_converters: optional `dict` of example converter function, where key is the name of the
        example parameter, and value is the converter function.
    """

    scenario_name = force_unicode(scenario_name, encoding)
    caller_module_path = get_caller_module_path()

    # Get the feature
    if features_base_dir is None:
        features_base_dir = get_features_base_dir(caller_module_path)
    feature = get_feature(features_base_dir, feature_name, encoding=encoding)

    # Get the scenario
    try:
        scenario = feature.scenarios[scenario_name]
    except KeyError:
        raise exceptions.ScenarioNotFound(
            u'Scenario "{scenario_name}" in feature "{feature_name}" in {feature_filename} is not found.'.format(
                scenario_name=scenario_name, feature_name=feature.name or "[Empty]", feature_filename=feature.filename
            )
        )

    scenario.example_converters = example_converters

    # Validate the scenario
    scenario.validate()

    return _get_scenario_decorator(
        feature=feature, feature_name=feature_name, scenario=scenario, scenario_name=scenario_name, encoding=encoding
    )


def get_features_base_dir(caller_module_path):
    default_base_dir = os.path.dirname(caller_module_path)
    return get_from_ini("bdd_features_base_dir", default_base_dir)


def get_steps_def_dir():
    config = CONFIG_STACK[-1]
    default_base_dir = os.path.join(os.getcwd(), "steps")
    path = os.path.normpath(get_from_ini("bdd_steps_def_dir", default_base_dir))
    if os.path.isabs(path):
        return path
    return str(config.rootdir.join(path))


def get_from_ini(key, default):
    """Get value from ini config. Return default if value has not been set.

    Use if the default value is dynamic. Otherwise set default on addini call.
    """
    config = CONFIG_STACK[-1]
    value = config.getini(key)
    return value if value != "" else default


def make_python_name(string):
    """Make python attribute name out of a given string."""
    string = re.sub(PYTHON_REPLACE_REGEX, "", string.replace(" ", "_"))
    return re.sub(ALPHA_REGEX, "", string).lower()


def make_python_docstring(string):
    """Make a python docstring literal out of a given string."""
    return u'"""{}."""'.format(string.replace(u'"""', u'\\"\\"\\"'))


def make_string_literal(string):
    """Make python string literal out of a given string."""
    return u"'{}'".format(string.replace(u"'", u"\\'"))


def get_python_name_generator(name):
    """Generate a sequence of suitable python names out of given arbitrary string name."""
    python_name = make_python_name(name)
    suffix = ""
    index = 0

    def get_name():
        return "test_{0}{1}".format(python_name, suffix)

    while True:
        yield get_name()
        index += 1
        suffix = "_{0}".format(index)


def scenarios(*feature_paths, **kwargs):
    """Parse features from the paths and put all found scenarios in the caller module.

    :param *feature_paths: feature file paths to use for scenarios
    """
    caller_locals = get_caller_module_locals()
    caller_path = get_caller_module_path()

    features_base_dir = kwargs.get("features_base_dir")
    if features_base_dir is None:
        features_base_dir = get_features_base_dir(caller_path)

    abs_feature_paths = []
    for path in feature_paths:
        if not os.path.isabs(path):
            path = os.path.abspath(os.path.join(features_base_dir, path))
        abs_feature_paths.append(path)
    found = False

    module_scenarios = frozenset(
        (attr.__scenario__.feature.filename, attr.__scenario__.name)
        for name, attr in caller_locals.items()
        if hasattr(attr, "__scenario__")
    )

    for feature in get_features(abs_feature_paths):
        for scenario_name, scenario_object in feature.scenarios.items():
            # skip already bound scenarios
            if (scenario_object.feature.filename, scenario_name) not in module_scenarios:

                @scenario(feature.filename, scenario_name, **kwargs)
                def _scenario():
                    pass  # pragma: no cover

                for test_name in get_python_name_generator(scenario_name):
                    if test_name not in caller_locals:
                        # found an unique test name
                        caller_locals[test_name] = _scenario
                        break
            found = True
    if not found:
        raise exceptions.NoScenariosFound(abs_feature_paths)
