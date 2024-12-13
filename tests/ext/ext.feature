Feature: test pytest-bdd step extension
  pytest-bdd step extension test, step params alias and constant step params e.g.

  Scenario Outline: test multi examples
    Then show result: <v1> <v2> <v3> <v4>

    Examples:
      | v1 | v2  |
      | k11  | k21 |
      | k12  | k22 |

    Examples:
      | v3  | v4  |
      | k31 | k41 |
      | k32 | k42 |
