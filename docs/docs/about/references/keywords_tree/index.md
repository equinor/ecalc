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
|Keyword               |Required| Description                                                                             |
|----------------------|--------|-----------------------------------------------------------------------------------------|
|[END](END)            |No      | Global end date for eCalc calculations.                                                 |
|[FACILITY_INPUTS](FACILITY_INPUTS)|Yes     | List of input files from facility characterization.                                     |
|[FUEL_TYPES](FUEL_TYPES)     |No      | Definition(s) the fuel type(s) being used in the model and the corresponding emissions. |
|[INSTALLATIONS](INSTALLATIONS)  |Yes     | Definitions of the system of energy consumers on each installation (e.g. platform).     |
|[START](START)          |No      | Global start date for eCalc calculations.                                               |
|[TIME_SERIES](TIME_SERIES)    |Yes     | List of input sources (files) containing all time series data.                          |
