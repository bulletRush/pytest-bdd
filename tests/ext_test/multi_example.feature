Feature: test pytest-bdd step extension
  pytest-bdd step extension test, step params alias and constant step params e.g.

  Examples:
  | v1  |
  | k11 |
  | k12 |

  Examples:
  | v2 |
  | k21 |
  | k22 |


  Scenario Outline: test multi examples
    Then show result: <v1> <v2> <v3> <v4>
    Examples:
      | v3  |
      | k31 |
      | k32 |
    Examples:
      | v4  |
      | k41 |
      | k42 |
    Examples:
      | v2  |
      | k23 |
      | k24 |
