"""pytest-bdd Exceptions."""
import six


class ScenarioIsDecoratorOnly(Exception):
    """Scenario can be only used as decorator."""


class ScenarioValidationError(Exception):
    """Base class for scenario validation."""


class ScenarioNotFound(ScenarioValidationError):
    """Scenario Not Found."""


class ExamplesNotValidError(ScenarioValidationError):
    """Example table is not valid."""


class ScenarioExamplesNotValidError(ScenarioValidationError):
    """Scenario steps parameters do not match declared scenario examples."""


class FeatureExamplesNotValidError(ScenarioValidationError):
    """Feature example table is not valid."""


class StepDefinitionNotFoundError(Exception):
    """Step definition not found."""


class InvalidStepParserError(Exception):
    """Invalid step parser."""


class NoScenariosFound(Exception):
    """No scenarios found."""


@six.python_2_unicode_compatible
class FeatureError(Exception):
    """Feature parse error."""

    message = u"{0}.\nLine number: {1}.\nLine: {2}.\nFile: {3}"

    def __str__(self):
        """String representation."""
        return self.message.format(*self.args)


@six.python_2_unicode_compatible
class ExampleError(Exception):
    """Feature parse error."""

    message = u"{0}.\nLine number: {1}.\nName: {2}"

    def __str__(self):
        """String representation."""
        return self.message.format(*self.args)
