# TIME_SERIES
 
[TIME_SERIES](/about/references/keywords/TIME_SERIES.md) /

## Description
This keyword defines the inputs for time dependent variables, or "reservoir
variables". For many fields, this may be only one reservoir simulation model. But in some
cases, one might have several sources for reservoir and other relevant time series variables.

For example, a field may have a reservoir simulation model for some areas and decline curves in other area of
the reservoir. There may also be tie-ins which are affecting the energy/emissions on the field
installations. Also, there may be time profiles for other variables.
Therefore, a set of sources may be specified with a name, path to data and type. The name is
later referred to in the system of energy consumers defined under [INSTALLATIONS](/about/references/keywords/INSTALLATIONS.md).

Reservoir variables and other time varying data not coming from a reservoir simulation model can
be specified in a [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) file.

### Required attributes for TIME_SERIES

| Attributes                                 | Description                                               |
|--------------------------------------------|-----------------------------------------------------------|
| [NAME](/about/references/keywords/NAME.md) | Time series reference name                                |
| [TYPE](/about/references/keywords/TYPE.md) | Time series type. Either MISCELLANEOUS or DEFAULT.        |
| [FILE](/about/references/keywords/FILE.md) | Path to input file                                        |

### Attributes dependent on TIME_SERIES TYPE

| TYPE            | [INTERPOLATION_TYPE](/about/references/keywords/INTERPOLATION_TYPE.md)               | [EXTRAPOLATION](/about/references/keywords/EXTRAPOLATION.md)                                                                                                     | [INFLUENCE_TIME_VECTOR](/about/references/keywords/INFLUENCE_TIME_VECTOR.md)                                                     |
|-----------------|--------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| DEFAULT         | Not allowed to specify. RIGHT is used                                                | Not possible to specify. FALSE is used                                                                                                                           | Optional. Default: TRUE                                                                                                          |
| MISCELLANEOUS   | Required: LEFT, RIGHT or LINEAR                                                      | Optional. Default: FALSE                                                                                                                                         | Optional. Default: TRUE                                                                                                          |
| **Description** | Defines how rates are interpolated between the given time steps (LEFT/RIGHT/LINEAR). | Defines whether the rates in the source should be set to 0 after the last time step (FALSE), or equal to value at last time step after the time interval (TRUE). | Determine if time steps should contribute to global time vector. TRUE or FALSE. At least one time vector is required to be TRUE. |

## Example
~~~~~~~~yaml
TIME_SERIES:
  - NAME: SIM1
    TYPE: DEFAULT
    FILE: /path_to_model1/model_data.csv
  - NAME: DATA2
    TYPE: MISCELLANEOUS # e.g. variable flare, compressor suction and discharge pressures
    FILE: inputs/somecsvdata.csv
    INFLUENCE_TIME_VECTOR: FALSE
    EXTRAPOLATION: TRUE
    INTERPOLATION_TYPE: RIGHT
~~~~~~~~

See [TIME SERIES](/about/modelling/setup/time_series.md) for more details about usage.