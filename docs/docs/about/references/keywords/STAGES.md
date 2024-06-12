# STAGES

[MODELS](/about/references/keywords/MODELS.md) /
[...] /
[STAGES](/about/references/keywords/STAGES.md)

## Description

This keyword is used to define each stage in a compression train model. This is to be defined for all compressor
models types.

## General usage

It is required to define the [INLET_TEMPERATURE](/about/references/keywords/INLET_TEMPERATURE.md) and a
[COMPRESSOR_CHART](/about/references/keywords/COMPRESSOR_CHART.md) for all compressor stages. It is also possible to
define a [PRESSURE_DROP_AHEAD_OF_STAGE](/about/references/keywords/PRESSURE_DROP_AHEAD_OF_STAGE.md) for each compressor
stage. 


## Use in `VARIABLE_SPEED_COMPRESSOR_TRAIN`

For variable speed compressor stages it is also possible to define a
[CONTROL_MARGIN](/about/references/keywords/CONTROL_MARGIN.md) and a
[CONTROL_MARGIN_UNIT](/about/references/keywords/CONTROL_MARGIN_UNIT.md)

A compressor stage in a [VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures.md)
can also have one or more fluid streams attached to it using the [STREAM](/about/references/keywords/STREAM.md) keyword,
or have an intermediate pressure target attached to itself using the [INTERSTAGE_CONTROL_PRESSURE](/about/references/keywords/INTERSTAGE_CONTROL_PRESSURE.md) keyword.


## Format

~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: <compressor type>
    ...
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
          COMPRESSOR_CHART: <reference to compressor chart model for first stage, must be defined in MODELS or FACILITY_INPUTS>
          PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
          ....
~~~~

## Use in `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`

A compressor stage in a [VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES](/about/modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures.md)
can also have one or more fluid streams attached to it using the [STREAM](/about/references/keywords/STREAM.md) keyword,
or have an intermediate pressure target attached to itself using the [INTERSTAGE_CONTROL_PRESSURE](/about/references/keywords/INTERSTAGE_CONTROL_PRESSURE.md) keyword.

:::warning Warning
Note that COMPRESSOR_TRAIN is not used for VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES.
STAGES is a list of all the stages in the compressor train. STREAMS is a list of all the fluid streams going in or out
of the compressor train.
:::

- For each stage, a temperature in Celsius must be defined. It is assumed that the gas is cooled down to this temperature ahead of the compression at this stage.
- A reference to a compressor chart needs to be specified for each stage.
- For the first stage, it is required to have **at least** one stream of INGOING type. In addition, `INTERSTAGE_CONTROL_PRESSURE` cannot be used on the first stage.
- Stages 2, ..., N may have a stream defined and it may be in- or outgoing. If an ingoing stream is defined, this stream
will be mixed with the outlet stream of the previous stage, obtaining a composition for the mixed fluid based on the
molar fractions and rate for each of them. If an outgoing stream is defined, the rate continuing to the next stage, will
be subtracted the rate of the outgoing stream.

### Format

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    ....
    STAGES:
      - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
        COMPRESSOR_CHART: <reference to a compressor chart model defined in MODELS>
        STREAM: <reference stream from STREAMS. Needs to be an INGOING type stream.>
        CONTROL_MARGIN: <Default value 0.0>
        PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
        CONTROL_MARGIN_UNIT: <FRACTION or PERCENTAGE, default is PERCENTAGE>
      - ...
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
    STAGES:
      - COMPRESSOR_CHART: 1_stage_chart
        INLET_TEMPERATURE: 20
        STREAM: 
          - 1_stage_inlet
      - COMPRESSOR_CHART: 2_stage_chart 
        INLET_TEMPERATURE: 30
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
