# MECHANICAL_EFFICIENCY

[MODELS](/about/references/MODELS.md) / 
[SHAFT](/about/references/SHAFT.md) /
[MECHANICAL_EFFICIENCY](/about/references/MECHANICAL_EFFICIENCY.md)

## Description

`MECHANICAL_EFFICIENCY` defines the ratio of useful mechanical work output to the total mechanical work input for a shaft system. It accounts for power losses in bearings, gearboxes, seals, and couplings.

The mechanical efficiency is used in a [SHAFT](/about/references/SHAFT.md) model to calculate the shaft power required from the driver:

$$
P_{shaft} = \frac{P_{gas}}{\eta_{mechanical}}
$$

## Format

~~~~yaml
MODELS:
  - NAME: <shaft name>
    TYPE: SHAFT
    MECHANICAL_EFFICIENCY: <value>
~~~~

:::note Simplified trains
For `SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN`, `MECHANICAL_EFFICIENCY` is set directly on the train model (not via a separate SHAFT). It applies uniformly to all stages and defaults to 1.0 if not specified.
:::

## Example

~~~~yaml
MODELS:
  - NAME: compressor_shaft
    TYPE: SHAFT
    MECHANICAL_EFFICIENCY: 0.95  # 95% efficiency, 5% losses
~~~~

## Value Range

| Constraint | Value | Description |
|------------|-------|-------------|
| Minimum | > 0 | Must be positive (exclusive) |
| Maximum | ≤ 1.0 | Cannot exceed 100% efficiency |

### Typical Values

| Drive Configuration | Typical Range | Typical Losses | Notes |
|---------------------|---------------|----------------|-------|
| Direct drive | 0.96 - 0.98 | 2-4% | Bearings (1-2%) + seals/couplings (1-2%) |
| With gearbox | 0.93 - 0.96 | 4-7% | Adds gearbox losses (2-3%) |

:::note
These are approximate ranges for the **total** mechanical efficiency of the drive train. The actual value depends on equipment design, operating conditions, and manufacturer data. A typical default of ~0.95 (5% losses) covers a common configuration with gearbox.
:::

## Physical Interpretation

The mechanical efficiency accounts for power losses in the drivetrain between 
the driver (motor/turbine) and the compressor, including:

- **Bearing losses**: Friction in shaft support bearings  
- **Gearbox losses**: Friction and churning in gear systems (if present)
- **Seal and coupling losses**: Minor friction in auxiliary components

:::note Constant efficiency assumption
In reality, frictional losses scale approximately with the square of rotational speed. 
However, eCalc assumes a **constant** mechanical efficiency across all operating points. 
Choose a representative value for typical operating conditions, or consult vendor data 
for the expected speed range.
:::

## See Also

- [SHAFT](/about/references/SHAFT.md)
- [EFFICIENCY](/about/references/EFFICIENCY.md)
- [POLYTROPIC_EFFICIENCY](/about/references/POLYTROPIC_EFFICIENCY.md)
