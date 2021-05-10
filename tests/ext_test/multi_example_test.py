from pytest_bdd import given, then, scenario


@then("show result: <v1> <v2> <v3> <v4>")
def step_then_show_result(v1="k10", v2="k20", v3="k30", v4="k40"):
    print ("show result: {0}_{1}_{2}_{3}".format(v1, v2, v3, v4))


@scenario('multi_example.feature', 'test multi examples')
def test_multi_examples():
    pass
