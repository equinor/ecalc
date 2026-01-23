# ADJUSTMENT (removed in v13.0)
[eCalc Model](index.md)
/ [FACILITY_INPUTS](FACILITY_INPUTS)
/ [ADJUSTMENT](ADJUSTMENT)

| Required | Child of        | Children/Options | Removed          |
|----------|-----------------|------------------|------------------|
| No       | FACILITY_INPUTS | CONSTANT <br />  FACTOR      | Removed in v13.0 |

:::warning
`ADJUSTMENT` has been removed in v13.0. See [Migration Guide](../migration_guides/v12.0_to_v13.0.md) on how to adjust your input data accordingly in >= v13.0
:::

## Description
For various reasons (degenerated equipment, liquid pumps, etc.), the predicted energy usage from
the facility input does not always match the historic usage. To account for this, adjustments
may be added to the facility input. Currently, linear adjustment to the energy usage is supported.

:::warning
Even though The [ADJUSTMENT](ADJUSTMENT) factor and constant can be added to any
[FACILITY_INPUTS](FACILITY_INPUTS), it is only
implemented and used for a small subset of equipment, namely: SAMPLED COMPRESSOR MODEL, TABULATED ENERGY USAGE MODEL,
[GENERATORSETS](/about/references/GENERATORSETS.md)
, PUMP MODEL (Single Speed, Variable Speed and System) and compressors in a compressor system.
If you are not sure, give it a test first.
:::

## Format
~~~~~~~~yaml
ADJUSTMENT:
  <ADJUSTMENT 1>: <VALUE>
  <ADJUSTMENT 2>: <VALUE>
~~~~~~~~

## Example
Say you have input that is off by a constant and percentage. You could fix this in the following way:

~~~~~~~~yaml
NAME: some_facility_input
FILE: filename.csv
TYPE: FACILITY_INPUT_TYPE
ADJUSTMENT:
  CONSTANT: 2
  FACTOR: 1.05
~~~~~~~~

The resulting energy consumption $E_\mathrm{adjusted}$, i.e. fuel or power, will then be

$$
E_\mathrm{adjusted} = 2 + 1.05 \times E_\mathrm{original}
$$

where $E_\mathrm{original}$ is the energy consumption before the adjustment.
