from pytest_bdd import then


@then("call general step with <value>")
def step_then_call_general_step(value):
    print(f"call general step with {value}")
