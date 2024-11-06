---
title: Simplified variable speed compressor train
sidebar_position: 2
---

The simplified variable speed compressor train model is a model of a compressor train where the inter stage pressures
are assumed based on an assumption of equal pressure fractions for each stage. Based on this, the compressor work is
calculated independently for each compressor as if it was a standalone compressor, neglecting that they are in fact on
the same shaft and thus have a common speed.

This model supports only 
`generic compressor charts`. See [compressor charts](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md) for more information. 

<span className="changed-from-version">
**Changed in version 9.0:** Only generic compressor charts are allowed. SINGLE_SPEED- and VARIABLE_SPEED charts are not allowed.
</span>
<br/>

In addition, a [FLUID MODEL](/about/modelling/setup/models/fluid_model.md) must be specified.

The model comes in two versions, one where the compressor stages are known (pre defined), and one where the compressor
stages are calculated at run-time based on input data.

## Format

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: <reference to fluid model, must be defined in MODELS
    COMPRESSOR_TRAIN: <compressor train specification>
    POWER_ADJUSTMENT_CONSTANT: <Optional constant MW adjustment added to the model>
    MAXIMUM_POWER: <Optional constant MW maximum power the compressor train can require>
    CALCULATE_MAX_RATE: <Optional. compressor train max standard rate [Sm3/day] in result if set to true. Default false. Use with caution. This will increase runtime significantly. >
~~~~~~~~

### Simplified compressor train model with known compressor stages
When the compressor stages are known, each stage is defined with a compressor chart and an inlet temperature:

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: <reference to fluid model>
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
          COMPRESSOR_CHART: <reference to compressor chart model for first stage, must be defined in MODELS or FACILITY_INPUTS>
        - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
          COMPRESSOR_CHART: <reference to compressor chart model for second stage, must be defined in MODELS or FACILITY_INPUTS>
        - ... and so forth for each stage in the train
    POWER_ADJUSTMENT_CONSTANT: <Optional constant MW adjustment added to the model>
    MAXIMUM_POWER: <Optional constant MW maximum power the compressor train can require>
~~~~~~~~

### Simplified compressor train model with unknown number of compressor stages
When the number of compressor stages are not known, one may specify the maximum pressure ratio per stage.
When the maximum pressure ratio is set, the number of compressors will be determined at run time (based on input data)
such that the number of compressors is large enough to ensure no pressure ratios are above a given maximum pressure
ratio per stage, but not larger.

This model is intended for (but not limited to) the use of a generic compressor chart. Especially one can test with the
generic compressor chart which are adjusted at run time (based on input data), for example to explore future
rebuilds/designs where no specifications/data is yet available from vendors et.c.

~~~~~~~~yaml
MODELS:
  - NAME: <model name>
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: <reference to fluid model>
    COMPRESSOR_TRAIN:
      MAXIMUM_PRESSURE_RATIO_PER_STAGE: <maximum pressure ratio per stage>
      COMPRESSOR_CHART: <reference to compressor chart model used for all stages, must be defined in [MODELS] or [FACILITY_INPUTS]>
      INLET_TEMPERATURE: <inlet temperature for all stages>
    POWER_ADJUSTMENT_CONSTANT: <Optional constant MW adjustment added to the model>
~~~~~~~~

## Examples

### A (single) compressor with a generic compressor chart, with design point calculated from input data, and fluid composition
~~~~~~~~yaml
MODELS:
  - NAME: generic_from_input_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: GENERIC_FROM_INPUT
    POLYTROPIC_EFFICIENCY: 0.75
    UNITS:
      EFFICIENCY: FRACTION

  - NAME: fluid_model_1
    TYPE: FLUID
    FLUID_MODEL_TYPE: COMPOSITION
    EOS_MODEL: SRK
    COMPOSITION:
        nitrogen: 0.74373
        CO2: 2.415619
        methane: 85.60145
        ethane: 6.707826
        propane: 2.611471
        i_butane: 0.45077
        n_butane: 0.691702
        i_pentane: 0.210714
        n_pentane: 0.197937
        n_hexane: 0.368786

  - NAME: simplified_compressor_model
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: fluid_model_1
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: generic_from_input_compressor_chart
~~~~~~~~

### A (single) turbine driven compressor with a generic compressor chart with design point and predefined composition

~~~~~~~~yaml
MODELS:
  - NAME: generic_from_design_point_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: GENERIC_FROM_DESIGN_POINT
    POLYTROPIC_EFFICIENCY: 0.75
    DESIGN_RATE: 7000
    DESIGN_HEAD: 50
    UNITS:
      RATE: AM3_PER_HOUR
      HEAD: KJ_PER_KG
      EFFICIENCY: FRACTION

  - NAME: medium_fluid
    TYPE: FLUID
    FLUID_MODEL_TYPE: PREDEFINED
    EOS_MODEL: SRK
    GAS_TYPE: MEDIUM

  - NAME: simplified_compressor_model
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: medium_fluid
    COMPRESSOR_TRAIN:
      STAGES:
        - INLET_TEMPERATURE: 30
          COMPRESSOR_CHART: generic_from_design_point_compressor_chart

  - NAME: compressor_train_turbine
    TYPE: TURBINE
    LOWER_HEATING_VALUE: 38 # MJ/Sm3
    TURBINE_LOADS: [0, 2.352, 4.589, 6.853, 9.125, 11.399, 13.673, 15.947, 18.223, 20.496, 22.767] # MW
    TURBINE_EFFICIENCIES: [0, 0.138, 0.210, 0.255, 0.286, 0.310, 0.328, 0.342, 0.353, 0.360, 0.362]  # fractions between 0 and 1

  - NAME: simplified_compressor_model_with_turbine
    TYPE: COMPRESSOR_WITH_TURBINE
    COMPRESSOR_MODEL: simplified_compressor_model
    TURBINE_MODEL: compressor_train_turbine
~~~~~~~~

### A compressor train with two stages where the first stage has unknown spec while the second generic compressor chart from design point

~~~~~~~~yaml
            MODELS:
              - NAME: generic_from_input_compressor_chart
                TYPE: COMPRESSOR_CHART
                CHART_TYPE: GENERIC_FROM_INPUT

              - NAME: generic_from_design_point_compressor_chart
                TYPE: COMPRESSOR_CHART
                CHART_TYPE: GENERIC_FROM_DESIGN_POINT
                POLYTROPIC_EFFICIENCY: 0.75
                DESIGN_RATE: 7000
                DESIGN_HEAD: 50
                UNITS:
                  RATE: AM3_PER_HOUR
                  HEAD: KJ_PER_KG
                  EFFICIENCY: FRACTION

              - NAME: dry_fluid
                TYPE: FLUID
                FLUID_MODEL_TYPE: PREDEFINED
                EOS_MODEL: SRK
                GAS_TYPE: DRY

              - NAME: simplified_compressor_train_model
                TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
                FLUID_MODEL: dry_fluid
                COMPRESSOR_TRAIN:
                  STAGES:
                    - INLET_TEMPERATURE: 30
                      COMPRESSOR_CHART: generic_from_input_compressor_chart
                    - INLET_TEMPERATURE: 30
                      COMPRESSOR_CHART: generic_from_design_point_compressor_chart
~~~~~~~~

### A compressor train where the number of stages are unknown

~~~~~~~~yaml
            MODELS:
              - NAME: generic_from_input_compressor_chart
                TYPE: COMPRESSOR_CHART
                CHART_TYPE: GENERIC_FROM_INPUT
                POLYTROPIC_EFFICIENCY: 0.75
                UNITS:
                  EFFICIENCY: FRACTION

              - NAME: dry_fluid
                TYPE: FLUID
                FLUID_MODEL_TYPE: PREDEFINED
                EOS_MODEL: SRK
                GAS_TYPE: DRY

              - NAME: simplified_compressor_train_model
                TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
                FLUID_MODEL: dry_fluid
                COMPRESSOR_TRAIN:
                  MAXIMUM_PRESSURE_RATIO_PER_STAGE: 3.5
                  COMPRESSOR_CHART: generic_from_input_compressor_chart
                  INLET_TEMPERATURE: 30
~~~~~~~~
