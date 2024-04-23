# TYPE

[...] / 
[TYPE](/about/references/keywords/TYPE.md) /

## Description
The [TYPE](/about/references/keywords/TYPE.md) is always a string. The allowed strings, and the resulting change in behavior,
will depend on where [TYPE](/about/references/keywords/TYPE.md) is used:

### Use in [FACILITY_INPUTS](/about/references/keywords/FACILITY_INPUTS.md)
- `ELECTRICITY2FUEL`
- `TABULAR`
- `COMPRESSOR_TABULAR`
- `PUMP_CHART_SINGLE_SPEED`
- `PUMP_CHART_VARIABLE_SPEED`

### Use in [TIME_SERIES](/about/references/keywords/TIME_SERIES.md)
- `MISCELLANEOUS`
- `DEFAULT`

### Use in [ENERGY_USAGE_MODEL](/about/references/keywords/ENERGY_USAGE_MODEL.md)
 - `DIRECT`
 - `COMPRESSOR`
 - `PUMP`
 - `COMPRESSOR_SYSTEM`
 - `PUMP_SYSTEM`
 - `TABULATED`
 - `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`

### Use in [MODELS](/about/references/keywords/MODELS.md)
- `FLUID`
- `VARIABLE_SPEED_COMPRESSOR_TRAIN`
- `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`
- `SINGLE_SPEED_COMPRESSOR_TRAIN`
- `TURBINE`
- `COMPRESSOR_WITH_TURBINE`
- `SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN`

### Use in [VENTING_EMITTERS](/about/references/keywords/VENTING_EMITTERS.md) from v8.13
- `DIRECT_EMISSION`
- `OIL_VOLUME`

## Format
~~~~~~~~yaml
TYPE: <type>
~~~~~~~~
