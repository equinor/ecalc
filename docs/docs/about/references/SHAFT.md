# SHAFT

[MODELS](/about/references/MODELS.md) / 
[SHAFT](/about/references/SHAFT.md)

## Description

A `SHAFT` model represents the mechanical coupling between a compressor and its driver (turbine, electric motor, etc.). It captures mechanical losses that occur in bearings, gearboxes, seals, and couplings.

The shaft model uses `MECHANICAL_EFFICIENCY` (η) to convert between gas power (thermodynamic power delivered to the gas) and shaft power (mechanical power required from the driver):

$$
P_{shaft} = \frac{P_{gas}}{\eta_{mechanical}}
$$

Where:
- $P_{shaft}$ is the shaft power (input from driver) in MW
- $P_{gas}$ is the gas power (thermodynamic work on gas) in MW  
- $\eta_{mechanical}$ is the mechanical efficiency (0 < η ≤ 1)

### Physical Interpretation

- **η = 1.0**: No mechanical losses (ideal shaft) - all driver power goes to gas compression
- **η = 0.95**: 5% of shaft power delivered by the turbine/motor is lost to friction (bearings, gearbox, seals, etc.)
- **η = 0.93**: 7% mechanical losses

:::tip
Use SHAFT with MECHANICAL_EFFICIENCY instead of the deprecated POWER_ADJUSTMENT_FACTOR and POWER_ADJUSTMENT_CONSTANT parameters. The SHAFT model provides a physically meaningful way to account for mechanical losses.
:::

## Format

~~~~yaml
MODELS:
  - NAME: <shaft name>
    TYPE: SHAFT
    MECHANICAL_EFFICIENCY: <efficiency value (0 < η ≤ 1)>
~~~~

## Example

### Basic Shaft Definition

~~~~yaml
MODELS:
  - NAME: main_compressor_shaft
    TYPE: SHAFT
    MECHANICAL_EFFICIENCY: 0.95  # 5% mechanical losses
~~~~

### Using Shaft with Compressor Train

~~~~yaml
MODELS:
  - NAME: compressor_shaft
    TYPE: SHAFT
    MECHANICAL_EFFICIENCY: 0.97

  - NAME: export_compressor
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: fluid_model_ref
    SHAFT: compressor_shaft  # Reference to shaft model
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: compressor_chart_ref
~~~~

## Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| NAME | string | Yes | - | Unique name for the shaft model |
| TYPE | string | Yes | - | Must be `SHAFT` |
| MECHANICAL_EFFICIENCY | number | Yes | - | Mechanical efficiency (0 < η ≤ 1). See [MECHANICAL_EFFICIENCY](/about/references/MECHANICAL_EFFICIENCY.md) for typical values. |

## Constraints

- `MECHANICAL_EFFICIENCY` must be greater than 0 and less than or equal to 1
- Each `SHAFT` model can only be referenced by one compressor train (physical constraint: one shaft cannot drive multiple independent trains)

## Migration from Legacy Parameters

If you're currently using `POWER_ADJUSTMENT_FACTOR`, you can migrate to the `SHAFT` model:

### Before (deprecated)
~~~~yaml
MODELS:
  - NAME: my_compressor
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
    POWER_ADJUSTMENT_FACTOR: 1.05  # 5% power increase
    ...
~~~~

### After (recommended)
~~~~yaml
MODELS:
  - NAME: my_shaft
    TYPE: SHAFT
    MECHANICAL_EFFICIENCY: 0.952  # ~5% mechanical losses (1/1.05 ≈ 0.952)

  - NAME: my_compressor
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
    SHAFT: my_shaft
    ...
~~~~

:::note
The relationship between the old factor and new efficiency is:
$$\eta_{mechanical} = \frac{1}{\text{POWER\_ADJUSTMENT\_FACTOR}}$$
:::

### POWER_ADJUSTMENT_CONSTANT

Migration from `POWER_ADJUSTMENT_CONSTANT` is not straightforward, as it was used for various purposes (calibration bias, fixed auxiliary loads, etc.) that don't map directly to mechanical efficiency. If you're using this parameter, please review your model to determine the original intent and contact eCalc support for migration guidance.

## See Also

- [COMPRESSOR_TRAIN_MODEL](/about/references/COMPRESSOR_TRAIN_MODEL.md)
- [MECHANICAL_EFFICIENCY](/about/references/MECHANICAL_EFFICIENCY.md)
- [POWER_ADJUSTMENT_FACTOR](/about/references/POWER_ADJUSTMENT_FACTOR.md) (deprecated)
