#!/usr/bin/env python
# -*- coding:utf-8 -*-
import os
import sys

import six

from pytest_bdd import scenario, then, when

if six.PY2:
    reload(sys)
    sys.setdefaultencoding("utf8")

CUR_DIR = os.path.dirname(os.path.abspath(__file__))


@when("in situation: 1", target_fixture="context", case=1)
@when("in situation: <case>", target_fixture="context")
def step_when_in_some_situation(case):
    default_d = {
        "k3": "hello world 你好，世界",
        "k4": "default",
        "k5": 10,
        "k6": 3.14,
        "k7": None,
        "k8": '',
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
def step_then_check_field(field, context, value="default"):
    print("check field: {0} is value: {1}({2}), except: {3}".format(
        field, value,
        type(value).__name__, context[field]))
    assert field in context
    assert context[field] == value


@scenario('ext.feature',
          'variant step test',
          features_base_dir=CUR_DIR,
          example_converters=dict(case=int))
def test_check_new_step():
    pass


@scenario('ext.feature',
          'default step value',
          features_base_dir=CUR_DIR)
def test_default_step_value():
    pass

