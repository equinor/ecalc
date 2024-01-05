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
| Keyword                                                                     |Required| Description                                                                             |
|-----------------------------------------------------------------------------|--------|-----------------------------------------------------------------------------------------|
| [END](/about/references/keywords/END.md)                                    |No      | Global end date for eCalc calculations.                                                 |
| [FACILITY_INPUTS](/about/references/keywords_tree/FACILITY_INPUTS/index.md) |Yes     | List of input files from facility characterization.                                     |
| [FUEL_TYPES](/about/references/keywords/FUEL_TYPES.md)                      |No      | Definition(s) the fuel type(s) being used in the model and the corresponding emissions. |
| [INSTALLATIONS](/about/references/keywords_tree/INSTALLATIONS/index.md)     |Yes     | Definitions of the system of energy consumers on each installation (e.g. platform).     |
| [START](/about/references/keywords/START.md)                                |No      | Global start date for eCalc calculations.                                               |
| [TIME_SERIES](/about/references/keywords_tree/TIME_SERIES/index.md)         |Yes     | List of input sources (files) containing all time series data.                          |
