import io
import os.path
import re
import textwrap
from collections import OrderedDict

import six
import json

from . import types, exceptions

SPLIT_LINE_RE = re.compile(r"(?<!\\)\|")
COMMENT_RE = re.compile(r"(^|(?<=\s))#")
STEP_PREFIXES = [
    ("Feature: ", types.FEATURE),
    ("Scenario Outline: ", types.SCENARIO_OUTLINE),
    ("Examples: Vertical", types.EXAMPLES_VERTICAL),
    ("Examples:", types.EXAMPLES),
    ("Scenario: ", types.SCENARIO),
    ("Background:", types.BACKGROUND),
    ("Given ", types.GIVEN),
    ("When ", types.WHEN),
    ("Then ", types.THEN),
    ("@", types.TAG),
    # Continuation of the previously mentioned step type
    ("And ", types.CONTINUE),
    ("But ", types.CONTINUE),
]


def split_line(line):
    """Split the given Examples line.

    :param str|unicode line: Feature file Examples line.

    :return: List of strings.
    """
    return [cell.replace("\\|", "|").strip() for cell in SPLIT_LINE_RE.split(line)[1:-1]]


def parse_line(line):
    """Parse step line to get the step prefix (Scenario, Given, When, Then or And) and the actual step name.

    :param line: Line of the Feature file.

    :return: `tuple` in form ("<prefix>", "<Line without the prefix>").
    """
    for prefix, _ in STEP_PREFIXES:
        if line.startswith(prefix):
            return prefix.strip(), line[len(prefix) :].strip()
    return "", line


def strip_comments(line):
    """Remove comments.

    :param str line: Line of the Feature file.

    :return: Stripped line.
    """
    res = COMMENT_RE.search(line)
    if res:
        line = line[: res.start()]
    return line.strip()


def get_step_type(line):
    """Detect step type by the beginning of the line.

    :param str line: Line of the Feature file.

    :return: SCENARIO, GIVEN, WHEN, THEN, or `None` if can't be detected.
    """
    for prefix, _type in STEP_PREFIXES:
        if line.startswith(prefix):
            return _type


def parse_feature(basedir, filename, encoding="utf-8"):
    """Parse the feature file.

    :param str basedir: Feature files base directory.
    :param str filename: Relative path to the feature file.
    :param str encoding: Feature file encoding (utf-8 by default).
    """
    abs_filename = os.path.abspath(os.path.join(basedir, filename))
    rel_filename = os.path.join(os.path.basename(basedir), filename)
    feature = Feature(
        scenarios=OrderedDict(),
        filename=abs_filename,
        rel_filename=rel_filename,
        line_number=1,
        name=None,
        tags=set(),
        examples=Examples(),
        background=None,
        description="",
    )
    scenario = None
    mode = None
    prev_mode = None
    description = []
    step = None
    multiline_step = False
    prev_line = None

    with io.open(abs_filename, "rt", encoding=encoding) as f:
        content = f.read()

    for line_number, line in enumerate(content.splitlines(), start=1):
        unindented_line = line.lstrip()
        line_indent = len(line) - len(unindented_line)
        if step and (step.indent < line_indent or ((not unindented_line) and multiline_step)):
            multiline_step = True
            # multiline step, so just add line and continue
            step.add_line(line)
            continue
        else:
            step = None
            multiline_step = False
        stripped_line = line.strip()
        clean_line = strip_comments(line)
        if not clean_line and (not prev_mode or prev_mode not in types.FEATURE):
            continue
        cur_mode = get_step_type(clean_line)
        if cur_mode == types.CONTINUE:
            if mode not in (types.GIVEN, types.WHEN, types.THEN):
                raise exceptions.FeatureError(
                    "can not detect line mode safe", line_number, clean_line, filename
                )
            cur_mode = None
        mode = cur_mode or mode

        allowed_prev_mode = (types.BACKGROUND, types.GIVEN, types.WHEN)

        if not scenario and prev_mode not in allowed_prev_mode and mode in types.STEP_TYPES:
            raise exceptions.FeatureError(
                "Step definition outside of a Scenario or a Background", line_number, clean_line, filename
            )

        if mode == types.FEATURE:
            if prev_mode is None or prev_mode == types.TAG:
                _, feature.name = parse_line(clean_line)
                feature.line_number = line_number
                feature.tags = get_tags(prev_line)
            elif prev_mode == types.FEATURE:
                description.append(clean_line)
            else:
                raise exceptions.FeatureError(
                    "Multiple features are not allowed in a single feature file",
                    line_number,
                    clean_line,
                    filename,
                )

        prev_mode = mode

        # Remove Feature, Given, When, Then, And
        keyword, parsed_line = parse_line(clean_line)
        if mode in [types.SCENARIO, types.SCENARIO_OUTLINE]:
            tags = get_tags(prev_line)
            if scenario:
                scenario.try_rock_current_examples()
                if len(scenario._steps) == 0:
                    raise exceptions.ScenarioValidationError(
                        "scenario not private step found: {0}".format(scenario.name))
            feature.scenarios[parsed_line] = scenario = Scenario(feature, parsed_line, line_number, tags=tags)
        elif mode == types.BACKGROUND:
            feature.background = Background(feature=feature, line_number=line_number)
        elif mode == types.EXAMPLES:
            (scenario or feature).try_rock_current_examples()
            mode = types.EXAMPLES_HEADERS
            (scenario or feature).examples.line_number = line_number
        elif mode == types.EXAMPLES_VERTICAL:
            mode = types.EXAMPLE_LINE_VERTICAL
            (scenario or feature).examples.line_number = line_number
        elif mode == types.EXAMPLES_HEADERS:
            (scenario or feature).examples.set_param_names([l for l in split_line(parsed_line) if l])
            mode = types.EXAMPLE_LINE
        elif mode == types.EXAMPLE_LINE:
            (scenario or feature).examples.add_example([l for l in split_line(stripped_line)])
        elif mode == types.EXAMPLE_LINE_VERTICAL:
            param_line_parts = [l for l in split_line(stripped_line)]
            try:
                (scenario or feature).examples.add_example_row(param_line_parts[0], param_line_parts[1:])
            except exceptions.ExamplesNotValidError as exc:
                if scenario:
                    raise exceptions.FeatureError(
                        """Scenario has not valid examples. {0}""".format(exc.args[0]),
                        line_number,
                        clean_line,
                        filename,
                    )
                else:
                    raise exceptions.FeatureError(
                        """Feature has not valid examples. {0}""".format(exc.args[0]),
                        line_number,
                        clean_line,
                        filename,
                    )
        elif mode and mode not in (types.FEATURE, types.TAG):
            step = Step(name=parsed_line, type=mode, indent=line_indent, line_number=line_number, keyword=keyword)
            if feature.background and not scenario:
                target = feature.background
            else:
                target = scenario
            target.add_step(step)
        prev_line = clean_line
    if scenario:
        scenario.try_rock_current_examples()
    feature.try_rock_current_examples()
    feature.description = u"\n".join(description).strip()
    return feature


class Feature(object):
    """Feature."""

    def __init__(self, scenarios, filename, rel_filename, name, tags, examples, background, line_number, description):
        self.scenarios = scenarios
        self.rel_filename = rel_filename
        self.filename = filename
        self.name = name
        self.tags = tags
        self.examples = examples
        self.name = name
        self.line_number = line_number
        self.tags = tags
        self.scenarios = scenarios
        self.description = description
        self.background = background
        self.examples_collections = []

    def try_rock_current_examples(self):
        if self.examples:
            self.examples_collections.append(self.examples)
        self.examples = Examples()
        return self.examples


class Scenario(object):

    """Scenario."""

    def __init__(self, feature, name, line_number, example_converters=None, tags=None):
        """Scenario constructor.

        :param pytest_bdd.parser.Feature feature: Feature.
        :param str name: Scenario name.
        :param int line_number: Scenario line number.
        :param dict example_converters: Example table parameter converters.
        :param set tags: Set of tags.
        """
        self.feature = feature
        self.name = name
        self._steps = []
        self.examples = Examples()
        self.line_number = line_number
        self.example_converters = example_converters
        self.tags = tags or set()
        self.failed = False
        self.test_function = None
        self.examples_collections = []

    def add_step(self, step):
        """Add step to the scenario.

        :param pytest_bdd.parser.Step step: Step.
        """
        step.scenario = self
        self._steps.append(step)

    @property
    def steps(self):
        """Get scenario steps including background steps.

        :return: List of steps.
        """
        result = []
        if self.feature.background:
            result.extend(self.feature.background.steps)
        result.extend(self._steps)
        return result

    @property
    def params(self):
        """Get parameter names.

        :return: Parameter names.
        :rtype: frozenset
        """
        return frozenset(sum((list(step.params) for step in self.steps), []))

    def try_rock_current_examples(self):
        if self.examples:
            self.examples_collections.append(self.examples)
        self.examples = Examples()
        return self.examples

    def get_example_params(self):
        """Get example parameter names."""
        s = set()
        for examples_collections in [self.examples_collections, self.feature.examples_collections]:
            for examples in examples_collections:
                s.update(examples.example_params)
        for step in self.steps:  # type: Step
            s.update(set(step.alias_params.values()))
        return s

    def get_duplicate_example_params(self):
        """Get example parameter names."""
        scenario_params = set()
        feature_params = set()
        for examples in self.examples_collections:
            scenario_params.update(examples.example_params)
        for examples in self.feature.examples_collections:
            feature_params.update(examples.example_params)
        return scenario_params.intersection(feature_params)

    def get_params(self, builtin=False):
        """Get converted example params."""
        for examples in self.examples_collections:
            yield examples.get_params(self.example_converters, builtin=builtin)
        duplicate_params = self.get_duplicate_example_params()
        for examples in self.feature.examples_collections:
            yield examples.get_params(self.example_converters, builtin=builtin, ignore_params=duplicate_params)

    def validate(self):
        """Validate the scenario.

        :raises ScenarioValidationError: when scenario is not valid
        """
        params = self.params
        example_params = self.get_example_params()
        # if params and example_params and params != example_params:
        # because we may use global example in fixture directly
        if params and example_params and not params.issubset(example_params):
            raise exceptions.ScenarioExamplesNotValidError(
                """Scenario "{0}" in the feature "{1}" has not valid examples. """
                """Set of step parameters {2} should match set of example values {3}.""".format(
                    self.name, self.feature.filename, sorted(params), sorted(example_params)
                )
            )


@six.python_2_unicode_compatible
class Step(object):
    class _SkipMark(object):
        pass

    """Step."""
    VARIANT_STEP_PARAM_RE = re.compile(r"(?<!\\)<(\w+)(\.([\w]*?))?:(.*?)>")  # variant step params regex
    GENERAL_STEP_PARAM_RE = re.compile(r"(?<!\\)<(\w+)>")  # general step params regex
    SKIP_MARK = _SkipMark()

    def __init__(self, name, type, indent, line_number, keyword):
        """Step constructor.

        :param str name: step name.
        :param str type: step type.
        :param int indent: step text indent.
        :param int line_number: line number.
        :param str keyword: step keyword.
        """
        self.name = name
        self.keyword = keyword
        self.lines = []
        self.indent = indent
        self.type = type
        self.line_number = line_number
        self.failed = False
        self.start = 0
        self.stop = 0
        self.scenario = None
        self.background = None
        self.constant_params = {}
        self.alias_params = {}
        self.alias_convert = {}

        self._init_step_args_convert()

    @staticmethod
    def _convert_bool(val):
        if isinstance(val, six.string_types):
            val = val.lower()
            if val == "true":
                return True
            elif val == "false":
                return False

            try:
                return bool(int(val))
            except ValueError:
                pass
            return bool(val)
        return bool(val)

    def _convert_value(self, key, convert, value):
        if convert is None:
            if value == "":
                self.constant_params[key] = self.SKIP_MARK
                return
            self.constant_params[key] = value
            return
        converts = {
            "i": int,
            "f": float,
            "I": int,
            "d": float,
            "b": self._convert_bool,
            "N": lambda x: None,  # use None value
            "E": lambda x: "",  # use empty string
            "S": lambda x: self.SKIP_MARK,  # skip, use step default value
            "A": None,  # alias to another args
            "l": lambda x: [a.strip() for a in x.split(",")],  # list
            "j": lambda x: json.loads(x),
        }
        e = exceptions.ExampleError(
            "unknown constant step value convert(valid: [{0}])".format(",".join(converts.keys())),
            self.line_number, self.name, convert
        )

        if convert[0] == "A":
            if len(convert) > 1:
                f = converts[convert[-1]]
                for c in convert[:-1][1:-1]:
                    if c not in converts:
                        raise e
                    f = lambda x: converts[c](f(x))
            else:
                f = lambda x: x

            self.alias_params[key] = value
            self.alias_convert[key] = lambda request: f(request.getfixturevalue(value))
        else:
            for c in convert:
                if c not in converts:
                    raise e
                if isinstance(value, list):
                    value = [converts[c](v) for v in value]
                else:
                    value = converts[c](value)
            self.constant_params[key] = value

    def _init_step_args_convert(self):
        for param in self.VARIANT_STEP_PARAM_RE.finditer(self.name):
            key = param.group(1)
            convert = param.group(3)
            val = param.group(4)
            self._convert_value(key, convert, val)
        self.raw_name = self.name
        self.name = self.VARIANT_STEP_PARAM_RE.sub(r"<\1>", self.name)

    def add_line(self, line):
        """Add line to the multiple step.

        :param str line: Line of text - the continuation of the step name.
        """
        self.lines.append(line)

    @property
    def name(self):
        """Get step name."""
        multilines_content = textwrap.dedent("\n".join(self.lines)) if self.lines else ""

        # Remove the multiline quotes, if present.
        multilines_content = re.sub(
            pattern=r'^"""\n(?P<content>.*)\n"""$',
            repl=r"\g<content>",
            string=multilines_content,
            flags=re.DOTALL,  # Needed to make the "." match also new lines
        )

        lines = [self._name] + [multilines_content]
        return "\n".join(lines).strip()

    @name.setter
    def name(self, value):
        """Set step name."""
        self._name = value

    def __str__(self):
        """Full step name including the type."""
        return '{type} "{name}"'.format(type=self.type.capitalize(), name=self.name)

    @property
    def params(self):
        """Get step params."""
        s = set(self.GENERAL_STEP_PARAM_RE.findall(self.raw_name))
        s.update(set(self.alias_params.values()))
        return tuple(s)


class Background(object):

    """Background."""

    def __init__(self, feature, line_number):
        """Background constructor.

        :param pytest_bdd.parser.Feature feature: Feature.
        :param int line_number: Line number.
        """
        self.feature = feature
        self.line_number = line_number
        self.steps = []

    def add_step(self, step):
        """Add step to the background."""
        step.background = self
        self.steps.append(step)


class Examples(object):

    """Example table."""

    def __init__(self):
        """Initialize examples instance."""
        self.example_params = []
        self.examples = []
        self.vertical_examples = []
        self.line_number = None
        self.name = None

    def set_param_names(self, keys):
        """Set parameter names.

        :param names: `list` of `string` parameter names.
        """
        self.example_params = [str(key) for key in keys]

    def add_example(self, values):
        """Add example.

        :param values: `list` of `string` parameter values.
        """
        self.examples.append(values)

    def add_example_row(self, param, values):
        """Add example row.

        :param param: `str` parameter name
        :param values: `list` of `string` parameter values
        """
        if param in self.example_params:
            raise exceptions.ExamplesNotValidError(
                """Example rows should contain unique parameters. "{0}" appeared more than once""".format(param)
            )
        self.example_params.append(param)
        self.vertical_examples.append(values)

    def get_params(self, converters, builtin=False, ignore_params=None):
        """Get scenario pytest parametrization table.

        :param converters: `dict` of converter functions to convert parameter values
        """
        if ignore_params is None:
            ignore_params = set()
        param_count = len(self.example_params)
        if self.vertical_examples and not self.examples:
            for value_index in range(len(self.vertical_examples[0])):
                example = []
                for param_index in range(param_count):
                    example.append(self.vertical_examples[param_index][value_index])
                self.examples.append(example)

        if self.examples:
            if ignore_params:
                example_params = [p for p in self.example_params if p not in ignore_params]
                if not example_params:
                    return []
            else:
                example_params = self.example_params

            params = []
            for example in self.examples:
                example = list(example)
                for index, param in enumerate(self.example_params):
                    if param in ignore_params:
                        continue
                    raw_value = example[index]
                    if converters and param in converters:
                        value = converters[param](raw_value)
                        if not builtin or value.__class__.__module__ in {"__builtin__", "builtins"}:
                            example[index] = value
                if ignore_params:
                    example = [e for idx, e in enumerate(example) if self.example_params[idx] not in ignore_params]
                params.append(example)
            return [example_params, params]
        else:
            return []

    def __bool__(self):
        """Bool comparison."""
        return bool(self.vertical_examples or self.examples)

    if six.PY2:
        __nonzero__ = __bool__


def get_tags(line):
    """Get tags out of the given line.

    :param str line: Feature file text line.

    :return: List of tags.
    """
    if not line or not line.strip().startswith("@"):
        return set()
    return set((tag.lstrip("@") for tag in line.strip().split(" @") if len(tag) > 1))


STEP_PARAM_RE = re.compile(r"\<(.+?)\>")
