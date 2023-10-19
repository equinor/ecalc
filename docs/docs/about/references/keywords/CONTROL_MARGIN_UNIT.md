# CONTROL_MARGIN_UNIT

[MODELS](/about/references/keywords/MODELS.md) /
[...] /
[STAGES](/about/references/keywords/STAGES.md)

## Description

This keyword defines the unit of the [surge control margin](/about/references/keywords/CONTROL_MARGIN.md) for a variable speed compressor chart.

The `CONTROL_MARGIN_UNIT` is given as a percentage or fraction of the rate difference between minimum- and maximum flow.

It is defined when setting up the stages in a [Variable speed compressor train model](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model.md) or [Variable speed compressor train model with multiple streams and pressures](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures.md).

It is currently only possible to define a surge control margin for variable speed compressors.

See [Surge control margin for variable speed compressor chart](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md) for more details.

### Format

~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: <reference to fluid model, must be defined in MODELS>
    ...
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
          COMPRESSOR_CHART: <reference to compressor chart model for first stage, must be defined in MODELS or FACILITY_INPUTS>
          CONTROL_MARGIN: <Default value is zero>
          CONTROL_MARGIN_UNIT: <FRACTION or PERCENTAGE, default is PERCENTAGE>
          ....
~~~~

### Example
~~~~yaml
MODELS:
  - NAME: compressor_model
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: fluid_model
    ...
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 20
          COMPRESSOR_CHART: 1_stage_chart
          CONTROL_MARGIN: 0.1
          CONTROL_MARGIN_UNIT: FRACTION
          ....
~~~~
