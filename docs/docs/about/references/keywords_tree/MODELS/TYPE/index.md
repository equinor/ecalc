---
sidebar_position: 2
---
# TYPE

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md)

## Description

Model type. The supported types are:

- [FLUID](/about/references/keywords_tree/MODELS/TYPE/FLUID/index.md)
- [COMPRESSOR_CHART](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_CHART/index.md)
- [SINGLE_SPEED_COMPRESSOR_TRAIN](/about/references/keywords_tree/MODELS/TYPE/SINGLE_SPEED_COMPRESSOR_TRAIN/index.md)
- [SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN](/about/references/keywords_tree/MODELS/TYPE/SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN/index.md)
- [VARIABLE_SPEED_COMPRESSOR_TRAIN](/about/references/keywords_tree/MODELS/TYPE/VARIABLE_SPEED_COMPRESSOR_TRAIN/index.md)
- [VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES](/about/references/keywords_tree/MODELS/TYPE/VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES/index.md)
- [TURBINE](/about/references/keywords_tree/MODELS/TYPE/TURBINE/index.md)
- [COMPRESSOR_WITH_TURBINE](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_WITH_TURBINE/index.md)

The documentation of each of these is found on the [Compressor Modelling](/about/modelling/setup/models/compressor_modelling/compressor_models_types/index.md) page.

### Format

~~~~~~~~yaml
MODELS:
  - NAME: <name of model, for reference>
    TYPE: <model type>
    <other keywords according to TYPE>
~~~~~~~~