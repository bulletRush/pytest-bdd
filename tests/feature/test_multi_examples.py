import textwrap
import pytest


def test_multi_examples(testdir):
    testdir.makefile(
        ".feature",
        steps=textwrap.dedent(
            """\
            Feature: test pytest-bdd step extension
              pytest-bdd step extension test, step params alias and constant step params e.g.

              Examples:
              | v1  |
              | k11 |
              | k12 |

              Examples:
              | v2 |
              | k21 |
              | k22 |


              Scenario Outline: test multi examples
                Then show result: <v1> <v2> <v3> <v4>
                Examples:
                  | v3  |
                  | k31 |
                  | k32 |
                Examples:
                  | v4  |
                  | k41 |
                  | k42 |
            """
        ),
    )
    testdir.makepyfile(
        textwrap.dedent(
            """\
            from pytest_bdd import given, then, scenario


            @then("show result: <v1> <v2> <v3> <v4>")
            def step_then_show_result(v1, v2, v3, v4):
                print ("show result: {0}_{1}_{2}_{3}".format(v1, v2, v3, v4))


            @scenario('steps.feature', 'test multi examples')
            def test_multi_examples():
                pass
            """
        )
    )
    result = testdir.runpytest("-v")
    result.assert_outcomes(passed=16, failed=0)
