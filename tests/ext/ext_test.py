#!/usr/bin/env python
from pytest_bdd import scenario, then

FEATURE_NAME = "ext.feature"


@then("show result: <v1> <v2> <v3> <v4>")
def step_then_show_result(v1, v2, v3, v4):
    print(f"\nshow result: {v1}_{v2}_{v3}_{v4}")


@scenario(FEATURE_NAME, "test multi examples")
def test_multi_examples():
    pass
