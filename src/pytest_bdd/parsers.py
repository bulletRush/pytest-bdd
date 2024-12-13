"""Step parsers."""

from __future__ import annotations

import abc
import re as base_re
from typing import TYPE_CHECKING, Any, TypeVar, cast, overload

import parse as base_parse
from _pytest.fixtures import FixtureRequest
from parse_type import cfparse as base_cfparse

from . import exceptions

if TYPE_CHECKING:
    from .parser import Step


class StepParser(abc.ABC):
    """Parser of the individual step."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abc.abstractmethod
    def parse_arguments(self, step: Step, request: FixtureRequest) -> dict[str, Any] | None:
        """Get step arguments from the given step name.

        :return: `dict` of step arguments
        """
        ...

    @abc.abstractmethod
    def is_matching(self, step: Step) -> bool:
        """Match given name with the step name."""
        ...


class re(StepParser):
    """Regex step parser."""

    def __init__(self, name: str, *args: Any, **kwargs: Any) -> None:
        """Compile regex."""
        super().__init__(name)
        self.regex = base_re.compile(self.name, *args, **kwargs)

    def parse_arguments(self, step: Step, request: FixtureRequest) -> dict[str, str] | None:
        """Get step arguments.

        :return: `dict` of step arguments
        """
        match = self.regex.fullmatch(step.name)
        if match is None:
            return None
        return match.groupdict()

    def is_matching(self, step: Step) -> bool:
        """Match given name with the step name."""
        return bool(self.regex.fullmatch(step.name))


class parse(StepParser):
    """parse step parser."""

    def __init__(self, name: str, *args: Any, **kwargs: Any) -> None:
        """Compile parse expression."""
        super().__init__(name)
        self.parser = base_parse.compile(self.name, *args, **kwargs)

    def parse_arguments(self, step: Step, request: FixtureRequest) -> dict[str, Any]:
        """Get step arguments.

        :return: `dict` of step arguments
        """
        s = cast(dict[str, Any], self.parser.parse(step.name).named)
        return s

    def is_matching(self, step: Step) -> bool:
        """Match given name with the step name."""
        try:
            p = self.parser.parse(step.name)
            return bool(p)
        except ValueError:
            return False


class cfparse(parse):
    """cfparse step parser."""

    def __init__(self, name: str, *args: Any, **kwargs: Any) -> None:
        """Compile parse expression."""
        super(parse, self).__init__(name)
        self.parser = base_cfparse.Parser(self.name, *args, **kwargs)


class string(StepParser):
    """Exact string step parser."""

    def parse_arguments(self, step: Step, request: FixtureRequest) -> dict:
        """No parameters are available for simple string step.

        :return: `dict` of step arguments
        """
        return {}

    def is_matching(self, step: Step) -> bool:
        """Match given name with the step name."""
        return self.name == step.name


class _SkipMark:
    pass


class AngleBracketsParser(StepParser):
    VARIANT_STEP_PARAM_RE = base_re.compile(r"(?<!\\)<(\w+)(\.([\w]?))?:(.*?)>")  # variant step params regex
    GENERAL_STEP_PARAM_RE = base_re.compile(r"(?<!\\)<(\w+)>")  # general step params regex
    SKIP_MARK = _SkipMark()

    @staticmethod
    def _convert_bool(val):
        if isinstance(val, str):
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

    def _convert_value(self, key: str, convert: str, value: str, step: Step, request: FixtureRequest):
        if convert is None:
            if value == "":
                return self.SKIP_MARK
            return value

        converts = {
            "i": int,
            "f": float,
            "I": int,
            "d": float,
            "b": self._convert_bool,
            "N": lambda x: None,  # use None value
            "E": lambda x: "",  # use empty string
            "S": lambda x: self.SKIP_MARK,  # skip, use step default value
            "A": lambda x: self._get_fixture_value(x, request),
            "l": lambda x: [a.strip() for a in x.split(",")],  # list
            "li": lambda x: [int(a) for a in x.split(",")],  # int list
            "lf": lambda x: [float(a) for a in x.split(",")],  # float list
        }
        if convert in converts:
            return converts[convert](value)

        valid_converts = ",".join(converts.keys())
        raise exceptions.StepError(
            f"unknown step value convert({convert}) in step({step.origin}), valid: {valid_converts})"
        )

    def _get_fixture_value(self, key: str, request: FixtureRequest):
        pytest_bdd_example = request.getfixturevalue("_pytest_bdd_example")
        if key in pytest_bdd_example:
            return pytest_bdd_example[key]
        else:
            return request.getfixturevalue(key)

    def parse_arguments(self, step: Step, request: FixtureRequest) -> dict[str, str]:
        d = {}

        for key in self.GENERAL_STEP_PARAM_RE.findall(step.origin):
            val = self._get_fixture_value(key, request)
            d[key] = val

        for param in self.VARIANT_STEP_PARAM_RE.finditer(step.origin):
            key = param.group(1)
            convert = param.group(3)
            val = param.group(4)
            val = self._convert_value(key, convert, val, step=step, request=request)
            if val == self.SKIP_MARK:
                continue
            d[key] = val
        return d

    def is_matching(self, step: Step) -> bool:
        s = self.VARIANT_STEP_PARAM_RE.sub(r"<\1>", step.origin)
        return s == self.name


TStepParser = TypeVar("TStepParser", bound=StepParser)


@overload
def get_parser(step_name: str) -> string: ...


@overload
def get_parser(step_name: TStepParser) -> TStepParser: ...


def get_parser(step_name: str | StepParser) -> StepParser:
    """Get parser by given name."""

    if isinstance(step_name, StepParser):
        return step_name

    if "<" in step_name:
        return AngleBracketsParser(step_name)
    return string(step_name)
