# CONTROL_MARGIN

[MODELS](/about/references/keywords/MODELS.md) /
[...] /
[STAGES](/about/references/keywords/STAGES.md) /
[CONTROL_MARGIN](/about/references/keywords/CONTROL_MARGIN.md)

## Description

This keyword defines the surge control margin for a single speed compressor chart or a variable speed compressor chart.

The `CONTROL_MARGIN` behaves as an alternate to the minimum flow line: For each chart curve (a single speed chart will have one, a variable speed chart will have at least two) the input will be 'cropped' to only include points to the right of the control line - modelling recirculation (ASV) from the correct control line.

The `CONTROL_MARGIN` is given as a percentage or fraction ([CONTROL_MARGIN_UNIT](/about/references/keywords/CONTROL_MARGIN_UNIT.md)) of the rate difference between minimum- and maximum flow, 
for the given speed. It is used to calculate the increase in minimum flow for each individual speed curve. 
It is defined when setting up the stages in a [Single speed compressor train model](/about/modelling/setup/models/compressor_modelling/compressor_models_types/single_speed_compressor_train_model.md), [Variable speed compressor train model](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model.md) or [Variable speed compressor train model with multiple streams and pressures](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures.md).

See [Surge control margin for variable speed compressor chart](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md) for more details.

## Use in [Single speed compressor train model](/about/modelling/setup/models/compressor_modelling/compressor_models_types/single_speed_compressor_train_model.md)
### Format

~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: SINGLE_SPEED_COMPRESSOR_TRAIN
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
    TYPE: SINGLE_SPEED_COMPRESSOR_TRAIN
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


>>>>>>> Stashed changes
## Use in [Variable speed compressor train model](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model.md)
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

## Use in [Variable speed compressor train model with multiple streams and pressures](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures.md)

### Format

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    ....
    STREAMS:
        - NAME: <name of stream 1>
          TYPE: INGOING
          FLUID_MODEL: <reference to fluid model, must be defined in MODELS>
        - NAME: <name of stream 2>
          TYPE: INGOING
          FLUID_MODEL: <reference to fluid model, must be defined in MODELS>
        - ...
        - NAME: <name of stream N>
          TYPE: OUTGOING # NB: No fluid definition for outgoing streams!
    STAGES:
      - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
        COMPRESSOR_CHART: <reference to a compressor chart model defined in MODELS>
        STREAM: <Optional>
          - <reference stream from STREAMS for one in- or outgoing stream. Optional>
          - <reference stream from STREAMS for another in- or outgoing stream. Optional>
        CONTROL_MARGIN: <Default value 0.0>
        CONTROL_MARGIN_UNIT: <FRACTION or PERCENTAGE, default is PERCENTAGE>
        PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
        INTERSTAGE_CONTROL_PRESSURE:
          UPSTREAM_PRESSURE_CONTROL: <pressure control>
          DOWNSTREAM_PRESSURE_CONTROL: <pressure control>
      - ...
~~~~~~~~

### Example

~~~~~~~~yaml
MODELS:
  - NAME: compressor_model
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    ....
    STREAMS:
      - NAME: 1_stage_inlet
        TYPE: INGOING
        FLUID_MODEL: fluid_model_1
      - NAME: 3_stage_inlet
        TYPE: INGOING
        FLUID_MODEL: fluid_model_2
      - NAME: 2_stage_outlet
        TYPE: OUTGOING
    STAGES:
      - COMPRESSOR_CHART: 1_stage_chart
        INLET_TEMPERATURE: 20
        STREAM: 
          - 1_stage_inlet
        CONTROL_MARGIN: 10
        CONTROL_MARGIN_UNIT: PERCENTAGE
      - COMPRESSOR_CHART: 2_stage_chart 
        INLET_TEMPERATURE: 30
        CONTROL_MARGIN: 15
        CONTROL_MARGIN_UNIT: PERCENTAGE
      - COMPRESSOR_CHART: 3_stage_chart 
        INLET_TEMPERATURE: 35
        STREAM: 
          - 2_stage_outlet
          - 3_stage_inlet
        INTERSTAGE_CONTROL_PRESSURE:
          UPSTREAM_PRESSURE_CONTROL: INDIVIDUAL_ASV_RATE  #1st and 2nd stage
          DOWNSTREAM_PRESSURE_CONTROL: INDIVIDUAL_ASV_RATE #3rd and 4th stage
      - COMPRESSOR_CHART: 4_stage_chart 
        INLET_TEMPERATURE: 15
~~~~~~~~
