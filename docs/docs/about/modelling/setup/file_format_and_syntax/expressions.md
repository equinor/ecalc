---
sidebar_position: 3
description: eCalc EXPRESSIONS
---
# Expressions
The variables needed in the energy functions for the variable consumers, may not always be directly found in the
reservoir inputs. For example, there may be two group rates that should be added to be
consistent with the net rate through a compressor system. Or, it may be that a pressure defined in a network node is
not equal to the pressure at the inlet/outlet of a compressor system and some delta pressure must be added.

To avoid forcing the users to define new variables in the simulation files/CSV data and also keep the data in the
consumer’s energy function consistent, the calculator supports expressions to define variables (and conditions in the
[CONDITIONS](/about/references/CONDITIONS.md).

:::warning
When creating new variables from CSV files make sure to choose the right interpolation type!
See [INTERPOLATION_TYPE](/about/references/INTERPOLATION_TYPE.md) for more information.
:::

## Available operators
As reservoir simulation vectors (and also CSV headers) may include mathematical operators
like `+`, `-` in their names, the operators must be surrounded by curly brackets, `{}`,
in the expressions. Logical operators (`>`, `>=`, `<`, `<=`, `==`, `!=`)
evaluates to `0` or `1`.

The following operators are supported:

|Operator|Description          |Example                                        |
|--------|---------------------|-----------------------------------------------|
|``{+}`` |Addition             |``2 {+} 1``                                    |
|``{-}`` |Subtraction          |``SIM;GAS {-} 10``                             |
|``{*}`` |Multiplication       |``SIM;GAS {*} 2``                              |
|``{/}`` |Division             |``SIM;GAS {/} 2``                              |
|``{^}`` |Power                |``SIM;GAS {^} 2``                              |
|``( )`` |Parentheses          |``( SIM;GAS {+} 2 ) {/} 2``                    |
|``<``   |Less than            |``SIM;GAS {+} (SIM1;OIL < 150) {*} 1000000``   |
|``<=``  |Less than or equal   |``SIM;GAS {+} (SIM1;OIL <= 150) {*} 1000000``  |
|``>``   |Greater than         |``SIM;GAS {+} (SIM1;OIL > 150) {*} 1000000``   |
|``>=``  |Greater than or equal|``SIM;GAS {+} (SIM1;OIL >= 150) {*} 1000000``  |
|``==``  |Equal                |``SIM;GAS {+} (SIM;FLAG == 1) {*} 1000000``    |
|``!=``  |Not equal            |``SIM;GAS {-} (SIM;FLAG != 1) {*} 1000000``    |


## Examples
### Combining data from different reservoir inputs
The rate through a gas injection compressor is the sum of injection rate for the field plus
some additional injection rate for a tie-in (whose data is specified in a CSV file with
key `SIM2`):

~~~~~~~~yaml
VARIABLES:
  total_rate_through_compressor:
    VALUE: SIM1;GAS_INJ {+} SIM2;GAS_INJ
~~~~~~~~

### Model of additional rate
The rate through a compressor is the produced rate plus some additional term. This term _Q_ is a function of pressures $P_{1}$ and $P_{2}$,

$$
Q =  25000 \cdot \sqrt{P_{1} \cdot \left( P_{2} - P_{1} \right)}
$$

The addition is only added when the reservoir gas rate is positive.

~~~~~~~~yaml
VARIABLES:
  rate:
    VALUE: SIM;GAS_PROD {+} ( SIM;GAS_PROD > 0 ) {*} 25000 {*} ( SIM;P1 {*} ( SIM;P2 {-} SIM;P1 ) ) {^} 0.5
~~~~~~~~

