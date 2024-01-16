---
title: YAML keywords tree
sidebar_position: 2
description: eCalc KEYWORDS
---
# Keywords
eCalc models are defined using keywords in `YAML` (YAML Ain't Markup Language) model files. This
page gives an overview of the top level keywords as well as and overview of all available keywords in
eCalc with a short description.

## Top level keywords
| Keywords defining sections                                                  | Required | Description                                                                                                                                        |
|-----------------------------------------------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| [TIME_SERIES](/about/references/keywords_tree/TIME_SERIES/index.md)         | Yes      | List of input sources (files) containing all time series data.                                                                                     |
| [FACILITY_INPUTS](/about/references/keywords_tree/FACILITY_INPUTS/index.md) | Yes      | List of input files from facility characterization.                                                                                                |
| [MODELS](/about/references/keywords_tree/MODELS/index.md)                   | No       | Definition(s) of model(s). These are later used as input to other models, or in the `INSTALLATIONS` part of the setup by referencing their `NAME`. |
| [FUEL_TYPES](/about/references/keywords_tree/FUEL_TYPES/index.md)           | No       | Definition(s) the fuel type(s) being used in the model and the corresponding emissions.                                                            |
| [VARIABLES](/about/references/keywords_tree/VARIABLES/index.md)             | No       | Define variables which can be used throughout the YAML file via the use of expressions                                                             |
| [INSTALLATIONS](/about/references/keywords_tree/INSTALLATIONS/index.md)     | Yes      | Definitions of the system of energy consumers on each installation (e.g. platform).                                                                |

| Other keywords                                                                | Required | Description                                                                                                                                        |
|-------------------------------------------------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| [START](START)                                                                | No       | Global start date for eCalc calculations.                                                                                                          |
| [END](END)                                                                    | No       | Global end date for eCalc calculations.                                                                                                            |
