# INTERSTAGE_CONTROL_PRESSURE

[INSTALLATIONS](INSTALLATIONS) /
[...] /
[ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL)  / [...] /
[INTERSTAGE_CONTROL_PRESSURE](INTERSTAGE_CONTROL_PRESSURE)

## Description

This keyword can **only** be utilised for a `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES` type, and it is used in two separate sections:

- `MODELS` - to define the upstream and downstream pressure control methods
- `ENERGY_USAGE_MODEL` - to define the interstage pressure

### Use in [MODELS](MODELS)

:::note
This keyword cannot be specified for the first stage, and it may only be used **once** in a given compression train.
:::

Under the `INTERSTAGE_CONTROL_PRESSURE` keyword, the [UPSTREAM_PRESSURE_CONTROL](UPSTREAM_PRESSURE_CONTROL) and [DOWNSTREAM_PRESSURE_CONTROL](DOWNSTREAM_PRESSURE_CONTROL) keywords can be specified.

#### Format

~~~~yaml
MODELS:
  - NAME: <compressor model name>
    TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
    ...
    STAGES:
      - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
        COMPRESSOR_CHART: <reference to a compressor chart model defined in MODELS>
        STREAM: <reference stream from STREAMS. Needs to be an INGOING type stream.>
        ...
      - INLET_TEMPERATURE: <inlet temperature in Celsius for stage>
        COMPRESSOR_CHART: <reference to a compressor chart model defined in MODELS>
        INTERSTAGE_CONTROL_PRESSURE:
            UPSTREAM_PRESSURE_CONTROL: <DOWNSTREAM_CHOKE / UPSTREAM_CHOKE / INDIVIDUAL_ASV_RATE> 
            DOWNSTREAM_PRESSURE_CONTROL: <DOWNSTREAM_CHOKE / UPSTREAM_CHOKE / INDIVIDUAL_ASV_RATE>
        ...
~~~~

The reason why upstream and downstream pressure control methods need to be specified is that the compression train is essentially split in two - before and after the interstage pressure. Thus, a control method for each "side" of the model needs to be defined.
See [Variable speed compressor train model with multiple streams and pressures](../../modelling/setup/models/compressor_modelling/compressor_models_types/variable_speed_compressor_train_model_with_multiple_streams_and_pressures) for more details.

### Use in [ENERGY_USAGE_MODEL](ENERGY_USAGE_MODEL)

Within the `ENERGY_USAGE_MODEL` section (**only** when [TYPE](TYPE) is set to `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`) the actual value for the interstage pressure is set in **bar**.
This can either be a single value or an [EXPRESSION](EXPRESSION.md).

#### Format

~~~~~~~~yaml
      - NAME: <reference name>
        ...
        ENERGY_USAGE_MODEL:
            TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
            ...
            INTERSTAGE_CONTROL_PRESSURE: <interstage control pressure value/expression>
            ...
~~~~~~~~

#### Example

~~~~~~~~yaml
      - NAME: export_compressor
        ...
        ENERGY_USAGE_MODEL:
            TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES
            ...
            SUCTION_PRESSURE: 10 # bar
            INTERSTAGE_CONTROL_PRESSURE: 40 #bar
            DISCHARGE_PRESSURE: 120 #bar
~~~~~~~~
