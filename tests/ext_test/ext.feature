Feature: test pytest-bdd step extension
  pytest-bdd step extension test, step params alias and constant step params e.g.

  Scenario Outline: variant step test
    When in situation: <case>
    Then return field: <field:k1> should has value: <value-v1>
    Then return field: <field:k2> should has value: <value-v2>
    Then return field: <field:k3> should has value: <value:hello world 你好，世界>
    Then return field: <field:k4> should has value: <value:>  # default value
    Then return field: <field:k5> should has value: <value.i:10>  # constant value convert
    Then return field: <field:k6> should has value: <value.f:3.14>  # constant value convert
    Examples:
      | case | v1  | v2  |
      | 1    | v11 | v12 |
      | 2    | v21 | v22 |
