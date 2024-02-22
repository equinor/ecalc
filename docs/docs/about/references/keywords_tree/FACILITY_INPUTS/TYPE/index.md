---
sidebar_position: 1
---
# TYPE

[MODELS](/about/references/keywords_tree/FACILITY_INPUTS/index.md) /
[TYPE](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/index.md)

## Description

Facility input type. The supported types are:

- [ELECTRICITY2FUEL](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/ELECTRICITY2FUEL.md)
- [TABULAR](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/TABULAR.md)
- [COMPRESSOR_TABULAR](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/COMPRESSOR_TABULAR.md)
- [PUMP_CHART_SINGLE_SPEED](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/PUMP_CHART_SINGLE_SPEED.md)
- [PUMP_CHART_VARIABLE_SPEED](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/PUMP_CHART_VARIABLE_SPEED.md)

The documentation of each of these is found under [TYPE](/about/references/keywords_tree/FACILITY_INPUTS/TYPE/index.md) 
and on the [Facility Inputs](/about/modelling/setup/facility_inputs/index.md) page.

### Format

~~~~~~~~yaml
MODELS:
  - NAME: <name of model, for reference>
    TYPE: <model type>
    <other keywords according to TYPE>
~~~~~~~~