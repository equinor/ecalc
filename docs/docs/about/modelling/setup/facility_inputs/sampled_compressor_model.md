---
title: Sampled compressor model
sidebar_position: 3
description: Sampled compressor model
---

The compressor model is set up in an external tool, and this model is sampled by
running a point set of rates and pressures which span the operational area of the compressor train. The sampled data (rates, inlet pressures, outlet pressures and total energy usage for all stages) are specified in a `.csv` file and
inputted into eCalc™. Each line in the `.csv` defines a point (rate, suction pressure, discharge pressure) and the total energy usage.

* For **electrically driven** compressor trains. The total energy usage should be given in megawatts (MW).

* For **turbine driven** compressor trains. It is recommended to give the total energy usage in megawatts (MW) and couple the compressor model to a turbine model. However, it is possible (for backward compatibility) to give the total energy usage as fuel usage in standard cubic meters per day (Sm<sup>3</sup>/day) and use the model directly. In this case, you can also provide a POWER (MW) column to calculate power for the shaft based on fuel usage.

* The latter (turbine driven compressor train) will at some point become deprecated as it is replaced by COMPRESSOR_WITH_TURBINE mentioned above.*

* Inside the convex hull defined by the input variables, there is a
  [`barycentric interpolation`](https://en.wikipedia.org/wiki/Barycentric_coordinate_system#Interpolation_on_a_triangular_unstructured_grid)
  based on a [`Delaunay triangulation`](https://en.wikipedia.org/wiki/Delaunay_triangulation).
* Outside the defined area, there may be extrapolations where this is reasonable, i.e.,

  * for rates lower than the defined rates, the table is extrapolated up to minimum
    flow (to mimic ASV (anti-surge valve)/recirculation valve)
  * the suction pressure is extrapolated down to the defined area
  * the discharge pressure is extrapolated up to defined area to mimic choking when the required
    head is lower than the compressor operational area.

## Format

The sampled compressor model is defined under the main keyword [`FACILITY_INPUTS`](/about/references/keywords/FACILITY_INPUTS.md) in the format

~~~~~~~~yaml
    NAME: <model name>
    FILE: <sampled_data>.csv
    TYPE: COMPRESSOR_TABULAR
~~~~~~~~

## Header requirements for the sampled compressor csv file

* ``POWER`` (and/or ``FUEL``)
* A minimum of one (but more are allowed) of the following:
    * ``RATE``
    * ``SUCTION_PRESSURE``
    * ``DISCHARGE_PRESSURE``

In cases where the model is directly used as a turbine/fuel driven compressor without coupling it to an eCalc turbine
model, ``POWER`` may be replaced by ``FUEL``.

:::info Shaft power reporting 

In the case ``FUEL`` is provided, it is also possible to specify ``POWER`` in the csv-file in order to calculate shaft power usage for fuel driven compressors
:::

If only ``POWER`` is provided, we assume that the compressor is electrical-driven
If ``FUEL`` is provided, we assume that the compressor is turbine-driven (also when both ``FUEL`` and ``POWER`` is given)

## Units

| Quantity                     | Units              |
|------------------------------|--------------------|
| ``POWER``                    | MW                 |
| ``RATE``                     | Sm<sup>3</sup>/day |
| ``SUCTION_PRESSURE``         | bar                |
| ``DISCHARGE_PRESSURE``       | bar                |
| ``FUEL``                     | Sm<sup>3</sup>/day |


## Example tables

### 1D example

| RATE    | POWER |
|---------|-------|
| 0       | 0     |
| 100000  | 10    |
| 1000000 | 10    |
| 2600000 | 15    |
| 4400000 | 20    |

### 3D example

| RATE     | SUCTION_PRESSURE | DISCHARGE_PRESSURE | POWER  |
|----------|------------------|--------------------|--------|
| 1.00E+06 | 10               | 12.72              | 0.3664 |
| 1.00E+06 | 10               | 26.21              | 2.293  |
| 1.00E+06 | 26               | 31.36              | 0.2739 |
| 1.00E+06 | 26               | 70.77              | 6.28   |
| 1.00E+06 | 34               | 41.21              | 0.368  |
| 1.00E+06 | 34               | 94.24              | 8.435  |
| 1.00E+06 | 78               | 94.12              | 0.7401 |
| 1.00E+06 | 78               | 231.6              | 22.46  |
| 6.00E+06 | 26               | 36.93              | 4.197  |
| 6.00E+06 | 26               | 57.43              | 7.32   |
| 6.00E+06 | 38               | 46.96              | 2.156  |
| 6.00E+06 | 38               | 106.2              | 9.557  |
| 6.00E+06 | 54               | 67.26              | 1.95   |
| 6.00E+06 | 54               | 155.6              | 14.35  |
| 6.00E+06 | 78               | 94.17              | 1.399  |
| 6.00E+06 | 78               | 231.6              | 22.46  |
| 1.10E+07 | 42               | 66.92              | 9.712  |
| 1.10E+07 | 42               | 81.63              | 11.89  |
| 1.10E+07 | 62               | 75.64              | 3.678  |
| 1.10E+07 | 62               | 180.8              | 16.94  |
| 1.10E+07 | 78               | 97.79              | 3.452  |
| 1.10E+07 | 78               | 231.6              | 22.46  |
