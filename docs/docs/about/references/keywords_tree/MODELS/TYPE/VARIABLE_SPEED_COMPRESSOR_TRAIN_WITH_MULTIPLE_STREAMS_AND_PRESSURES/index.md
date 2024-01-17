---
sidebar_position: 2
---
# VARIABLE_SPEED_COMPRESSOR_TRAIN_WITH_MULTIPLE_STREAMS_AND_PRESSURES

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md)

## Description

Model type. The supported types are:

- [FLUID](/about/references/keywords_tree/MODELS/TYPE/FLUID/index.md)
- [COMPRESSOR_CHART](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_CHART/index.md)
- [SINGLE_SPEED_COMPRESSOR_TRAIN](/about/references/keywords_tree/MODELS/TYPE/SINGLE_SPEED_COMPRESSOR_TRAIN/index.md)
- `SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN`
- `VARIABLE_SPEED_COMPRESSOR_TRAIN`
- `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`
- `TURBINE`
- `COMPRESSOR_WITH_TURBINE`

The documentation of each of these is found on the [Compressor Modelling](/about/modelling/setup/models/compressor_modelling/compressor_models_types/index.md) page.

### Format

~~~~~~~~yaml
MODELS:
  - NAME: <name of model, for reference>
    TYPE: <model type>
    <other keywords according to TYPE>
~~~~~~~~