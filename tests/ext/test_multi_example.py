import textwrap


def test_multi_examples(testdir):
    testdir.makefile(
        ".feature",
        steps=textwrap.dedent(
            """\
            Feature: test pytest-bdd step extension
              pytest-bdd step extension test, step params alias and constant step params e.g.

              Scenario Outline: test multi examples
                Then show result: <v1> <v2> <v3> <v4>
                Examples:
                  | v1  | v2 |
                  | 1 | k21 |
                  | 2 | k22 |
                Examples:
                  | v3  | v4 |
                  | k31 | k41 |
                  | k32 | k42 |
            """
        ),
    )
    testdir.makepyfile(
        textwrap.dedent(
            """\
            from pytest_bdd import given, then, scenario, parsers


            @then(parsers.parse("show result: {v1:d} {v2} {v3} {v4}"))
            def step_then_show_result(v1, v2, v3, v4):
                print ("show result: {0}_{1}_{2}_{3}".format(v1, v2, v3, v4))


            @scenario('steps.feature', 'test multi examples')
            def test_multi_examples():
                pass
            """
        )
    )
    result = testdir.runpytest("-v")
    result.assert_outcomes(passed=4, failed=0)


def test_multi_examples2(testdir):
    testdir.makefile(
        ".feature",
        steps=textwrap.dedent(
            """\
            Feature: test pytest-bdd step extension
              pytest-bdd step extension test, step params alias and constant step params e.g.

              Scenario Outline: test multi examples
                Then show result: <v1> <v2> <v3> <v4>
                Examples:
                  | v1  | v2 |
                  | k11 | k21 |
                  | k12 | k22 |
                Examples:
                  | v3  | v4 |
                  | k31 | k41 |
                  | k32 | k42 |
            """
        ),
    )
    testdir.makepyfile(
        textwrap.dedent(
            """\
            from pytest_bdd import given, then, scenario, parsers


            @then("show result: <v1> <v2> <v3> <v4>")
            def step_then_show_result(v1, v2, v3, v4):
                print ("show result: {0}_{1}_{2}_{3}".format(v1, v2, v3, v4))


            @scenario('steps.feature', 'test multi examples')
            def test_multi_examples():
                pass
            """
        )
    )
    result = testdir.runpytest("--capture=fd", "-v")
    result.assert_outcomes(passed=4, failed=0)
