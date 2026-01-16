# MECHANICAL_EFFICIENCY

[MODELS](/about/references/MODELS.md) /
[MECHANICAL_EFFICIENCY](/about/references/MECHANICAL_EFFICIENCY.md)

## Description

`MECHANICAL_EFFICIENCY` defines the ratio of useful mechanical work output to the total mechanical work input for the compressor drivetrain. It accounts for power losses in bearings, gearboxes, seals, and couplings.

The mechanical efficiency is used to calculate the shaft power required from the driver:

$$
P_{shaft} = \frac{P_{gas}}{\eta_{mechanical}}
$$

Where:
- $P_{shaft}$ is the shaft power (input from driver) in MW
- $P_{gas}$ is the gas power (thermodynamic work on gas) in MW  
- $\eta_{mechanical}$ is the mechanical efficiency (0 < η ≤ 1)

## Format

~~~~yaml
MODELS:
  - NAME: <compressor train name>
    TYPE: <VARIABLE_SPEED_COMPRESSOR_TRAIN | SINGLE_SPEED_COMPRESSOR_TRAIN | SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN | VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES>
    MECHANICAL_EFFICIENCY: <value>  # Optional, default 1.0
    ...
~~~~

## Example

~~~~yaml
MODELS:
  - NAME: export_compressor
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
    MECHANICAL_EFFICIENCY: 0.95  # 95% efficiency, 5% losses
    FLUID_MODEL: medium_gas
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: compressor_chart_ref
~~~~

## Value Range

| Constraint | Value | Description |
|------------|-------|-------------|
| Minimum | > 0 | Must be positive (exclusive) |
| Maximum | ≤ 1.0 | Cannot exceed 100% efficiency |
| Default | 1.0 | No mechanical losses (ideal drivetrain) |

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

- [EFFICIENCY](/about/references/EFFICIENCY.md)
- [POLYTROPIC_EFFICIENCY](/about/references/POLYTROPIC_EFFICIENCY.md)
- [Mechanical Efficiency Migration Guide](/about/migration_guides/mechanical_efficiency.md)
