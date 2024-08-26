# COMPRESSOR_CHART

[MODELS](/about/references/MODELS.md) /
[...] /
[STAGES](/about/references/STAGES.md) /
[COMPRESSOR_CHART](/about/references/COMPRESSOR_CHART.md)


## Description
This is a keyword used in [COMPRESSOR MODELLING](/about/modelling/setup/models/compressor_modelling/compressor_models_types/index.md) when defining the individual stages of a compressor train.
It is a necessary input parameter which is a reference to a [compressor chart model](/about/modelling/setup/models/compressor_modelling/compressor_charts/index.md) defined in [MODELS](/about/references/MODELS.md).


## Format

~~~~~yaml
MODELS:
  - NAME: <model name>
    ...
    COMPRESSOR_TRAIN:
      STAGES:
        - COMPRESSOR_CHART: <reference to compressor chart model>
    ...
~~~~~

## Example

~~~~~yaml
MODELS:
  - NAME: compressor_train
    ...
    COMPRESSOR_TRAIN:
      STAGES:
        - COMPRESSOR_CHART: stage1_compressor_chart
    ...
~~~~~
