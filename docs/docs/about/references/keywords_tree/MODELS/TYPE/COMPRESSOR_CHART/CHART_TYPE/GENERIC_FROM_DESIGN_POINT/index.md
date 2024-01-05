---
sidebar_position: 3
---
# GENERIC_FROM_DESIGN_POINT

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md) :
[COMPRESSOR_CHART](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_CHART/index.md) /
[CHART_TYPE](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_CHART/CHART_TYPE/index.md) : 
[GENERIC_FROM_DESIGN_POINT](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_CHART/CHART_TYPE/GENERIC_FROM_DESIGN_POINT/index.md)

## Description 
A generic compressor chart with predefined design point. It is an "average" chart of 
compressors used on the NCS and cannot be expected to be equal to
the actual chart for a compressor which has been designed and delivered. However, 
it can be a good first estimation of how a chart may be for a future process not 
yet in the design phase. 

This chart will not replace any future compressor curves and it may not be accurate in comparison to the final compressor curve; however, it is a good method to capture the major effects (such as  `ASV` (anti-surge valve) recirculation). 
With this method it is possible to view how a "typical" compressor curve would react a large spread in the data set. If the design point is set within the middle of the data spread, points with rates lower than the minimum flow will have some recirculation; whilst, too high or unrealistic rates will not be solved. This is an essential difference in comparison to the generic chart with its design point calculated from input data (which is covered in `Generic compressor chart with design point calculated from input data`), which will shift the entire compressor curve to solve for even the highest rate and head points. 

Unified generic compressor chart:

![](../generic_unified_compressor_chart.png)

The compressor chart is created by scaling the unified generic compressor chart in the figure above with a design actual 
rate and head. Note that the rate is here in the units *am3/hr* which is NOT EQUAL to *Sm3/hr*. 
The units *am3/hr* refers to the volumetric rate at inlet conditions (inlet pressure and temperature), and it will differ from the inputted standard rates
due to the difference in density.
The design polytropic head is given in either *kJ/kg*, *m* or J/kg, `UNITS`.

The generic compressor chart is currently accompanied by a fixed polytropic efficiency (polytropic efficiency
variations within the chart may be supported in the future).

### Format
~~~~~~~~yaml
MODELS:
  - NAME: <name of chart, for reference>
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: GENERIC_FROM_DESIGN_POINT
    POLYTROPIC_EFFICIENCY: <polytropic efficiency of the compressor (fixed number)>
    DESIGN_RATE: <design rate>
    DESIGN_HEAD: <design polytropic head>
    UNITS:
      RATE: <rate unit, currently only AM3_PER_HOUR supported>
      HEAD: <polytropic head unit, M, KJ_PER_KG, JOULE_PER_KG supported>
      EFFICIENCY: <polytropic efficiency unit, FRACTION and PERCENTAGE.>
~~~~~~~~

### Example
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
~~~~~~~~

For this method it is important to note that only `Simplified variable speed compressor train model` is supported. 

### Example
~~~~~~~~yaml
MODELS:
  - NAME: generic_compression_train_design_point
    TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
    FLUID_MODEL: sample_fluid
    PRESSURE_CONTROL: UPSTREAM_CHOKE
    COMPRESSOR_TRAIN:
      STAGES:
        - COMPRESSOR_CHART: generic_from_design_point_compressor_chart
          INLET_TEMPERATURE: 30
~~~~~~~~

