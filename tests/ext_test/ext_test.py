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


@when("in situation: <case>", target_fixture="context")
def step_when_in_some_situation(case):
    return {
        "1": {
            "k1": "v11",
            "k2": "v12",
            "k3": "hello world 你好，世界",
        },
        "2": {
            "k1": "v21",
            "k2": "v22",
            "k3": "hello world 你好，世界",
        },
    }[str(case)]


@then("return field: <field> should has value: <value>")
def step_then_check_field(field, value, context):
    print("check field: {0} is value: {1}".format(field, value))
    assert field in context
    assert context[field] == value


@scenario('ext.feature',
          'variant step test',
          features_base_dir=CUR_DIR,
          example_converters=dict(case=int))
def test_check_new_step():
    pass
