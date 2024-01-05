---
sidebar_position: 4
---
# GENERIC_FROM_INPUT

[MODELS](/about/references/keywords_tree/MODELS/index.md) /
[TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md) :
[COMPRESSOR_CHART](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_CHART/index.md) /
[CHART_TYPE](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_CHART/CHART_TYPE/index.md) : 
[GENERIC_FROM_INPUT](/about/references/keywords_tree/MODELS/TYPE/COMPRESSOR_CHART/CHART_TYPE/GENERIC_FROM_INPUT/index.md)

## Description 
:::caution Caution
Beware that using this functionality in a `COMPRESSOR_SYSTEM energy usage model` can give some unwanted effects.
E.g. splitting/halving the rates into two equal compressor trains will in effect change the compressor chart for a
compressor set up with GENERIC_FROM_INPUT compared to running the full rate through a single compressor train.
Consider using a single design point instead.
:::

A generic compressor chart with design point calculated from input data.
This generic chart is also based on the unified generic compressor chart:

![](../generic_unified_compressor_chart.png)

However, in this case the design point is not specified when setting up the model, instead it is estimated at run time and is entirely based on the inputted data set. 
An algorithm is used to set a design point such that all the input data is within the capacity. 
Even if there is a large spread in the data, all data points will solve. High rate/head data points will just be covered by the curve; whilst low rate points outside the minimum flow point will have recirculation. 

This method has one major potential downside in comparison to the `Generic compressor chart with predefined design point`. As all data points will be covered by the compressor curve, if there is an extremely large or unrealistic head or rate value, the other more "normal" data points will be impacted and will either result in a large head adjustment (via upstream/downstream choking) or it will have a large recirculation rate. This has the potential to skew the entire data set solely due to one unrealistic data point.  Thus, if this generic chart is utilised it is important to make sure that unrealistic data is filtered out.

### Format
~~~~~~~~yaml
MODELS:
  - NAME: <name of chart, for reference>
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: GENERIC_FROM_INPUT
    POLYTROPIC_EFFICIENCY: <polytropic efficiency of the compressor (fixed number)>
    UNITS:
      EFFICIENCY: <polytropic efficiency unit, FRACTION and PERCENTAGE.>
~~~~~~~~

### Example
~~~~~~~~yaml
MODELS:
  - NAME: generic_from_input_compressor_chart
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: GENERIC_FROM_INPUT
    POLYTROPIC_EFFICIENCY: 0.75
    UNITS:
      EFFICIENCY: FRACTION
~~~~~~~~
