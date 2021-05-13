from pytest_bdd import given, then, scenario


# @then("show result: <v1> <v2> <v3> <v4>")
# def step_then_show_result(v1, v2="k20", v3="k30", v4="k40", k5=None, k6=10):
#     print ("show result: {0}_{1}_{2}_{3}_{4}_{5}".format(v1, v2, v3, v4, k5, k6))


@scenario('multi_example.feature', 'test multi examples')
def test_multi_examples():
    pass
