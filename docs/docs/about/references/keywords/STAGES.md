# STAGES

[MODELS](/about/references/keywords/MODELS.md) /
[...] /
[STREAMS](/about/references/keywords/STREAMS.md)

## Description

This keyword is used to define each stage in a compression train model. This is to be defined for all compressor models types.

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
          ....
~~~~

## Use in `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`

`STAGES` is a list of all the stages in the compressor train.

- For each stage, a temperature in Celsius must be defined. It
is assumed that the gas is cooled down to this temperature ahead of the compression at this stage.
- A reference to a
compressor chart needs to be specified for each stage.
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
