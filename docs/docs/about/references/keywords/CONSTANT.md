# CONSTANT

[FACILITY_INPUTS](FACILITY_INPUTS) /
[ADJUSTMENT](ADJUSTMENT) /
[CONSTANT](CONSTANT)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| No         | `ADJUSTMENT`              | None                               |

## Description
The keyword [CONSTANT](CONSTANT) can be used for adjustment of input data with a constant.

## Format
~~~~~~~~yaml
CONSTANT: <VALUE>
~~~~~~~~

## Example
Say you have input that that is off by -10 [some units].
You could fix this like:

~~~~~~~~yaml
NAME: some_facility_input
FILE: filename.csv
TYPE: FACILITY_INPUT_TYPE
ADJUSTMENT:
  CONSTANT: -10
~~~~~~~~

The resulting energy consumption $E_\mathrm{adjusted}$, i.e. fuel or power, will then be

$$
E_\mathrm{adjusted} = E_\mathrm{original} - 10
$$

where $E_\mathrm{original}$ is the energy consumption before the adjustment.
