# FACILITY_INPUTS

[FACILITY_INPUTS](/about/references/keywords/FACILITY_INPUTS.md)

| Required   | Child of                  | Children/Options                   |
|------------|---------------------------|------------------------------------|
| Yes        | None                      | `ADJUSTMENT` <br />  `FILE` <br /> `HEAD_MARGIN` <br /> `TYPE`           |

## Description
This part of the setup defines input files that characterize various facility elements. Each facility element is
specified in a list. These are later used as input in the [INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md) part of the setup by referencing their
[NAME](/about/references/keywords/NAME.md).

All facility inputs are in essence a `CSV` (Comma separated file) file that specifies input data to a model that
calculates how much energy the equipment is using depending on the operating mode/throughput. There are multiple
[supported types](#supported-types).

## Supported types
The facility input type is defined using the [TYPE](/about/references/keywords/TYPE.md) keyword and defines the type of model applied
to the data in this file. The input files are in `CSV` (Comma separated file) format. The paths to the input files may be either absolute or relative to the setup file.

The supported types are:

- `ELECTRICITY2FUEL`
- `TABULAR`
- `COMPRESSOR_TABULAR`
- `PUMP_CHART_SINGLE_SPEED`
- `PUMP_CHART_VARIABLE_SPEED`

See [FACILITY INPUTS](/about/modelling/setup/facility_inputs/index.md) for details about each of the above supported types and their usage.