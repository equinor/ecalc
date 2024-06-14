# COMPRESSOR_TRAIN

## Description

This keyword is necessary when defining a compressor model. It relates to defining the actual
[STAGES](/about/references/keywords/STAGES.md) in the compressor model.

## Format

~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: <compressor model type>
    FLUID_MODEL: <reference to fluid model, must be defined in MODELS>
    COMPRESSOR_TRAIN: 
      STAGES:
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
          COMPRESSOR_CHART: <reference to compressor chart model for first stage, must be defined in MODELS or FACILITY_INPUTS>
          PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
          COMPRESSOR_CHART: <reference to compressor chart model for second stage, must be defined in MODELS or FACILITY_INPUTS>
          PRESSURE_DROP_AHEAD_OF_STAGE: <Pressure drop before compression stage [in bar]>
        - ... and so forth for each stage in the train        
    ...
~~~~
