# EXPRESSION
 
[VARIABLES](VARIABLES) / 
[EXPRESSION](EXPRESSION)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| No         | `VARIABLES`         | `None`   |

## Description
Expression for a `variable<VARIABLES>` using `EXPRESSIONS`

## Format
~~~~~~~~yaml
EXPRESSION: <expression>
~~~~~~~~

## Example

With time series reference

~~~~~~~~yaml
EXPRESSION: time_series_ref_1;vector_name_1 {+} time_series_ref_2;vector_name_2 {*} (time_series_ref_3;vector_name_3 > 0)
~~~~~~~~

With variable reference

~~~~~~~~yaml
EXPRESSION: $var.variable_name1 {+} $var.variable_name2
~~~~~~~~
