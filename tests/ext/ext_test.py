#!/usr/bin/env python
from pytest_bdd import scenario, then, when

FEATURE_NAME = "ext.feature"


@then("show result: <v1> <v2> <v3> <v4>")
def step_then_show_result(v1, v2, v3, v4):
    print(f"\nshow result: {v1}_{v2}_{v3}_{v4}")


@scenario(FEATURE_NAME, "test multi examples")
def test_multi_examples():
    pass


# @when("in situation: 1", target_fixture="context", case=1)
@when("in situation: <case>", target_fixture="context")
def step_when_in_some_situation(case):
    default_d = {
        "k3": "hello world 你好，世界",
        "k4": "default",
        "k5": 10,
        "k6": 3.14,
        "k7": None,
        "k8": "",
        "k9": 10,
        "k10": 3.14,
        "k11": "default",
        "k12": True,
        "k13": True,
        "k14": False,
        "k15": False,
        "k16": False,
        "k17": False,
        "k18": True,
    }
    d = {
        "1": {
            "k1": "v11",
            "k2": "v12",
        },
        "2": {
            "k1": "v21",
            "k2": "v22",
        },
    }
    for _, v in d.items():
        v.update(default_d)
    return d[str(case)]


@then("return field: <field> should has value: <value>")
def step_then_check_field(field, value, context):
    print(f"check field: {field} is value: {value}")
    assert field in context
    assert context[field] == value


@scenario(FEATURE_NAME, "variant step test")
def test_check_new_step():
    pass


@scenario(FEATURE_NAME, "default step value")
def test_default_step_value():
    pass
