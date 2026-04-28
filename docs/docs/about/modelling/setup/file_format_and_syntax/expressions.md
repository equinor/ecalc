---
sidebar_position: 3
description: eCalc EXPRESSIONS
---
# Expressions

The variables needed in the energy functions for consumers may not always be directly available in the
reservoir inputs. For example, two group rates may need to be added to represent the net rate through a
compressor system, or a pressure offset must be applied between a network node and the compressor inlet.

Expressions allow you to define derived quantities from time-series data without modifying simulation files.
They can be used in [VARIABLES](/about/references/VARIABLES.md), [CONDITION](/about/references/CONDITION.md),
[CONDITIONS](/about/references/CONDITIONS.md), and most numeric fields throughout the YAML file.

:::warning
When creating new variables from CSV files make sure to choose the right interpolation type!
See [INTERPOLATION_TYPE](/about/references/INTERPOLATION_TYPE.md) for more information.
:::

## Operators {/* #operators */}

Because reservoir simulation vector names (and CSV headers) may contain `+`, `-`, `*`, `/` as part of their
names, **arithmetic operators must be wrapped in curly brackets** — e.g. `{+}` instead of `+`.

Comparison operators (`>`, `>=`, `<`, `<=`, `==`, `!=`) do **not** require curly brackets and evaluate
to `1.0` (true) or `0.0` (false).

| Operator | Description           | Example                                              |
|----------|-----------------------|------------------------------------------------------|
| `{+}`    | Addition              | `SIM;GAS {+} SIM2;GAS`                              |
| `{-}`    | Subtraction           | `SIM;GAS {-} 10`                                    |
| `{*}`    | Multiplication        | `SIM;GAS {*} 2`                                     |
| `{/}`    | Division              | `SIM;GAS {/} 2`                                     |
| `{^}`    | Power                 | `SIM;GAS {^} 2`                                     |
| `( )`    | Parentheses           | `( SIM;GAS {+} 2 ) {/} 2`                           |
| `<`      | Less than             | `(SIM;OIL < 150) {*} 1000000`                       |
| `<=`     | Less than or equal    | `(SIM;OIL <= 150) {*} 1000000`                      |
| `>`      | Greater than          | `(SIM;OIL > 150) {*} 1000000`                       |
| `>=`     | Greater than or equal | `(SIM;OIL >= 150) {*} 1000000`                      |
| `==`     | Equal                 | `(SIM;FLAG == 1) {*} 1000000`                       |
| `!=`     | Not equal             | `(SIM;FLAG != 1) {*} 1000000`                       |

## Order of operations {/* #order-of-operations */}

Operators are evaluated in the following order. Higher precedence operators bind more tightly.
Operators at the same level are evaluated **left to right** unless noted otherwise.

| Precedence  | Operator(s)                  | Notes                                |
|-------------|------------------------------|--------------------------------------|
| 1 (highest) | `( )`                        | Parentheses — always evaluated first |
| 2           | `{^}`                        | Power — **right to left**            |
| 3           | `{*}` `{/}`                  | Multiply, divide — left to right     |
| 4           | `{+}` `{-}`                  | Add, subtract — left to right        |
| 5 (lowest)  | `==` `!=` `<` `>` `<=` `>=` | Comparisons — left to right          |

:::important
**Arithmetic operators have higher precedence than comparison operators.**
This is the most common source of unexpected results. When a comparison result is used as a
factor (multiplied by something), it **must** be wrapped in parentheses.
:::

### Arithmetic before comparisons

Without parentheses, arithmetic is applied before the comparison:

```
SIM;GAS {+} SIM;EXTRA > 1000
→  (SIM;GAS {+} SIM;EXTRA) > 1000   ✓ arithmetic first, then compare
```

A comparison used as a multiplier must be parenthesised.
Without parentheses, the multiplication binds to the literal on the other side of the comparison:

```
# Missing parentheses around comparison:
(SIM;FLAG == 1) {*} SIM;RATE        ← correct
SIM;FLAG == 1 {*} SIM;RATE          ← parsed as  SIM;FLAG == (1 {*} SIM;RATE)  ✗
```

### Right-associative power

`{^}` binds **right to left**: `a {^} b {^} c` evaluates as `a {^} (b {^} c)`.

```
2 {^} 3 {^} 2  =  2 {^} (3 {^} 2)  =  2^9  =  512
               ≠  (2 {^} 3) {^} 2   =  8^2  =  64
```

Use explicit parentheses if you need left-to-right evaluation: `(2 {^} 3) {^} 2`.

## Conditional expressions {/* #conditional-expressions */}

Comparison operators return `0.0` (false) or `1.0` (true) as floating-point numbers.
Multiplying by a condition is the standard way to apply a value only when a criterion is met:

```yaml
VARIABLES:
  # Add extra gas only when the platform flag is active:
  adjusted_gas:
    VALUE: SIM;GAS {+} (SIM;FLAG == 1) {*} SIM;EXTRA_GAS

  # Zero out rate when below a threshold:
  effective_rate:
    VALUE: SIM;RATE {*} (SIM;RATE > 100)
```

Multiple conditions can be combined using arithmetic. Because comparisons return 0 or 1,
`{*}` acts as a logical AND:

```yaml
VARIABLES:
  # Both conditions must be true:
  rate_when_both_active:
    VALUE: SIM;RATE {*} (SIM;FLAG_A == 1) {*} (SIM;FLAG_B == 1)
```

:::tip
Always wrap each comparison in its own parentheses. This avoids operator-precedence surprises
and makes intent clear.
:::

## Notes {/* #notes */}

### Division by zero

Division by zero and any `NaN` values silently evaluate to `0`. An expression like
`SIM;RATE {/} SIM;COUNT` will not error when `SIM;COUNT` is zero — it produces `0` for
those time steps.

### Negative numeric literals

A leading `-` sign is not valid at the start of a string expression.
Use subtraction from zero instead:

```yaml
# ERROR:
VALUE: -5 {*} SIM;GAS         # ← parse error, '-' is not a valid token start

# Correct:
VALUE: 0 {-} 5 {*} SIM;GAS   # evaluates as  0 - (5 * GAS)  =  -5 * GAS  ✓
```

Note that `0 {-} 5 {*} SIM;GAS` is `0 - (5 * GAS)` because multiplication has higher
precedence — which gives the correct result for negation.

A plain numeric YAML value such as `CONSTANT: -5` is not affected; YAML parses `-5` as a
number before eCalc sees it.

### Scientific notation

Numeric literals support scientific notation:

```yaml
VALUE: SIM;GAS {*} 1.5e-3    # multiply by 0.0015
VALUE: SIM;RATE {+} 2.5e6    # add 2 500 000
```

## Examples

### Combining data from multiple sources

The total rate through a gas injection compressor is the sum of two injection streams:

```yaml
VARIABLES:
  total_injection_rate:
    VALUE: SIM1;GAS_INJ {+} SIM2;GAS_INJ
```

### Conditional additional rate

The rate through a compressor equals the produced rate plus an additional term $Q$ that is
only active when gas production is positive:

$$
Q = 25000 \cdot \sqrt{P_1 \cdot (P_2 - P_1)}
$$

```yaml
VARIABLES:
  rate:
    VALUE: SIM;GAS_PROD {+} (SIM;GAS_PROD > 0) {*} 25000 {*} (SIM;P1 {*} (SIM;P2 {-} SIM;P1)) {^} 0.5
```

The parentheses around `(SIM;GAS_PROD > 0)` are **required**. Without them, `{*} 25000`
would bind to the right-hand side of `>`, changing the comparison to
`SIM;GAS_PROD > (0 {*} 25000)` and discarding the intended multiplication entirely.

### Using defined variables in other expressions

Variables defined under `VARIABLES` can be referenced elsewhere using `$var.<name>`:

```yaml
VARIABLES:
  base_rate:
    VALUE: SIM1;GAS_PROD {+} SIM2;GAS_PROD

  adjusted_rate:
    VALUE: $var.base_rate {*} (SIM;PRESSURE > 50)
```