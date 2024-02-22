---
sidebar_position: 4
---
# MODELS

[MODELS](/about/references/keywords_tree/MODELS/index.md)

## Description
Each element is specified in a list. These are later used as input to other models, or in the
[INSTALLATIONS](/about/references/keywords_tree/INSTALLATIONS/index.md) part of the setup by referencing their
[NAME](/about/references/keywords_tree/MODELS/NAME.md).

This part of the setup specifies models not having any input data and/or multi level models, that is models which use
other models (from both [MODELS](/about/references/keywords_tree/MODELS/index.md) and from [FACILITY_INPUTS](/about/references/keywords_tree/FACILITY_INPUTS/index.md)).

The keyword [TYPE](/about/references/keywords_tree/MODELS/TYPE/index.md) defines the type of model. Each model type may have separate keywords.

### Format

~~~~~~~~yaml
MODELS:
  - NAME: <name of model, for reference>
    TYPE: <model type>
    <other keywords according to TYPE>
~~~~~~~~

