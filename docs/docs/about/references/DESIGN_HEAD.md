# DESIGN_HEAD

## Description

`DESIGN_HEAD` is required to be specified under the [MODELS](/about/references/MODELS.md) keyword when
the model is of [TYPE](/about/references/TYPE.md) `COMPRESSOR_CHART` **and** the [CHART_TYPE](/about/references/CHART_TYPE.md)
is `GENERIC_FROM_DESIGN_POINT`. For more details see [Generic compressor chart with predefined design point](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md#generic-compressor-chart-with-predefined-design-point)

## Format

~~~~yaml
MODELS:
  - NAME: <name of model>
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: <only for GENERIC_FROM_DESIGN_POINT>
    POLYTROPIC_EFFICIENCY: <polytropic efficiency of the compressor (fixed number)>
    DESIGN_RATE: <design rate> 
    DESIGN_HEAD: <design head>
    UNITS:
      RATE: <rate unit, currently only AM3_PER_HOUR supported>
      HEAD: <polytropic head unit, M, KJ_PER_KG, JOULE_PER_KG supported>
      EFFICIENCY: <polytropic efficiency unit, FRACTION and PERCENTAGE.>
    ...
~~~~

## Example

~~~~yaml
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
~~~~