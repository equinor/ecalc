---
sidebar_position: 1
---
# SINGLE_SPEED

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md):
[COMPRESSOR_CHART](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_CHART/index.md) /
[CHART_TYPE](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_CHART/CHART_TYPE/index.md): 
[SINGLE_SPEED](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_CHART/CHART_TYPE/SINGLE_SPEED/index.md)

## Description 
The single speed chart type allows a single compressor curve for one speed, using the keyword [CURVE](/about/references/keywords/CURVE)

### Format
~~~~~~~~yaml
MODELS:
  - NAME: <name of chart, for reference>
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: SINGLE_SPEED
    UNITS:
      RATE: <rate unit, currently only AM3_PER_HOUR supported>
      HEAD: <polytropic head unit, M, KJ_PER_KG, JOULE_PER_KG supported>
      EFFICIENCY: <polytropic efficiency unit, FRACTION and PERCENTAGE.>
    CURVE:
      - SPEED: <shaft speed for this curve, a number>
        RATE: <list of rate values for this chart curve>
        HEAD: <list of polytropic head values for this chart curve>
        EFFICIENCY: <list of polytropic efficiency values for this chart curve>
~~~~~~~~

### Example
~~~~~~~~yaml
MODELS:
  - NAME: predefined_single_speed_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: SINGLE_SPEED
    UNITS:
      RATE: AM3_PER_HOUR
      HEAD: M
      EFFICIENCY: FRACTION
    CURVE:
      - SPEED: 7500
        RATE: [2900, 3503, 4002, 4595.0]
        HEAD: [8412.9, 7996, 7363, 6127]
        EFFICIENCY: [0.72, 0.75, 0.74, 0.70]
~~~~~~~~

:::tip Tip
It is also possible to input single speed compressor chart as csv file.

#### Format

~~~~~~~~yaml
CURVE:
  FILE: <csv file with single speed compressor chart>
~~~~~~~~

#### Example

~~~~~~~~yaml
CURVE:
  FILE: compressor_chart_single_speed.csv
~~~~~~~~
:::