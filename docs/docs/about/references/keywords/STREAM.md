# STREAM

[MODELS](/about/references/keywords/MODELS.md) /
[...] / [STAGES](/about/references/keywords/STAGES.md)
[STREAMS](/about/references/keywords/STREAMS.md)

:::note
This keyword is not to be confused with `STREAMS` - which is also utilised for `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`
:::

## Description

This keyword can **only** be utilised for a `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES` model type and is used under the [STAGES](/about/references/keywords/STAGES.md) keyword.

This is used to refer a [STAGE](/about/references/keywords/STAGES.md) to a previously defined [STREAMS](/about/references/keywords/STREAMS.md). 

## Format

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    ...
    STAGES:
      - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
        COMPRESSOR_CHART: <reference to a compressor chart model defined in MODELS>
        STREAM: <reference stream from STREAMS. Needs to be an INGOING type stream.>
      - ...
      - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
        COMPRESSOR_CHART: <reference to a compressor chart model defined in MODELS>
        STREAM: <Optional>
        - <reference stream from STREAMS for one in- or outgoing stream. Optional>
        - <reference stream from STREAMS for another in- or outgoing stream. Optional>
~~~~~~~~

## Example

~~~~~~~~yaml
MODELS:
  - NAME: compressor_model
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    ...
    STAGES:
      - COMPRESSOR_CHART: 1_stage_chart
        INLET_TEMPERATURE: 20
        STREAM: 
          - 1_stage_inlet
      ...
~~~~~~~~
