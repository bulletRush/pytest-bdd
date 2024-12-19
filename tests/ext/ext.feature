Feature: test pytest-bdd step extension
  pytest-bdd step extension test, step params alias and constant step params e.g.

  Background:
    When in situation: 1

  Examples:
  | case | g1  | v1  |
  | 1    | g11 | g12 |
  | 2    | g21 | g22 |

  Scenario Outline: test multi examples
    Then show result: <v1> <v2> <v3> <v4>

    Examples:
      | v1  | v2  |
      | k11 | k21 |
      | k12 | k22 |

    Examples:
      | v3  | v4  |
      | k31 | k41 |
      | k32 | k42 |

  Scenario Outline: variant step test
    When in situation: <case>
    Then return field: <field:k1> should has value: <value.A:v1>
    Then return field: <field:k2> should has value: <value.A:v2>
    Then return field: <field:k3> should has value: <value:hello world 你好，世界>
    Then return field: <field:k4> should has value: <value.S:>  # default value convert
    Then return field: <field:k5> should has value: <value.i:10>  # integer constant value convert
    Then return field: <field:k6> should has value: <value.f:3.14>  # float constant value convert
    Then return field: <field:k7> should has value: <value.N:>  # None constant value convert
    Then return field: <field:k8> should has value: <value.E:>  # empty constant value convert
    Then return field: <field:k9> should has value: <value.I:10>  # integer constant value convert
    Then return field: <field:k10> should has value: <value.d:3.14>  # float constant value convert
    Then return field: <field:k11> should has value: <value:>  # default value convert
    Then return field: <field:k12> should has value: <value.b:True>  # bool value convert
    Then return field: <field:k13> should has value: <value.b:true>  # bool value convert
    Then return field: <field:k14> should has value: <value.b:False>  # bool value convert
    Then return field: <field:k15> should has value: <value.b:false>  # bool value convert
    Then return field: <field:k16> should has value: <value.b:>  # bool value convert
    Then return field: <field:k17> should has value: <value.b:0>  # bool value convert
    Then return field: <field:k18> should has value: <value.b:1>  # bool value convert
    Then return field: <field:k19> should has value: <value.li:1,2,3>  # int list
    Then return field: <field:k20> should has value: <value.Ai:v3>  # alias to int
    Then return field: <field:k21> should has value: <value.lf:1.1, 2.2, 3.3>  # alias to float

    Examples:
      | case | v1  | v2  | v3 |
      | 1    | v11 | v12 | 10 |
      | 2    | v21 | v22 | 20 |

  Scenario: default step value
    When in situation: 1
    Then return field: <field:k1> should has value: <value:v11>
    Then return field: <field:k2> should has value: <value:v12>

  Scenario: call general step
    When in situation: 1
    Then call general step with <value:hello>
