---
title: YAML Overview
sidebar_position: 1001
toc_max_heading_level: 5
---

# YAML Overview

:::info
This page is auto-generated from the eCalc Pydantic model. Last generated: 2026-03-23.
:::

<div className="yaml-reference">

## TIME_SERIES {#time_series}

Defines the inputs for time dependent variables, or 'reservoir variables'.

```yaml
TIME_SERIES:
  - TYPE: <type>
    NAME: <name>
    FILE: <file>
    INFLUENCE_TIME_VECTOR: <influence_time_vector>
```

### TYPE *(required)* {#time_series-type}

The type of the component

Allowed values: `DEFAULT` &#124; `MISCELLANEOUS`

<div className="yaml-variant">

#### DEFAULT {#time_series-default}

*Standard time series. Uses right-interpolation and no extrapolation.*

</div>

<div className="yaml-variant">

#### MISCELLANEOUS {#time_series-miscellaneous}

*Time series with configurable interpolation and extrapolation.*

```yaml
EXTRAPOLATION: <extrapolation>
INTERPOLATION_TYPE: <interpolation_type>
```

- **EXTRAPOLATION**<span id="time_series-miscellaneous-extrapolation"></span><br/>  Defines whether the rates in the source should be set to 0 after last time step or constant equal to value at last time step after time interval. (<code>true / false</code> · default: <code>False</code>)

- **INTERPOLATION_TYPE** *(required)*<span id="time_series-miscellaneous-interpolation_type"></span><br/>  Defines how the time series are interpolated between input time steps.<br/>  Allowed values: <code>LEFT ∣ RIGHT ∣ LINEAR</code>

</div>

### NAME *(required)* {#time_series-name}

Name of the time series. (<code>text</code>)

### FILE *(required)* {#time_series-file}

Specifies the name of a time series input file. (<code>text</code>)

### INFLUENCE_TIME_VECTOR {#time_series-influence_time_vector}

Determines if the time steps in this input source will contribute to the global time vector.

<code>true / false</code> · default: <code>True</code>

---

## FACILITY_INPUTS {#facility_inputs}

Defines input files which characterize various facility elements.

```yaml
FACILITY_INPUTS:
  - TYPE: <type>
    NAME: <name>
    FILE: <file>
```

### TYPE *(required)* {#facility_inputs-type}

The type of the component

Allowed values: `ELECTRICITY2FUEL` &#124; `TABULAR` &#124; `COMPRESSOR_TABULAR` &#124; `PUMP_CHART_SINGLE_SPEED` &#124; `PUMP_CHART_VARIABLE_SPEED`

<div className="yaml-variant">

#### ELECTRICITY2FUEL {#facility_inputs-electricity2fuel}

*Tabular model mapping electric power to fuel consumption for a generator set.*

</div>

<div className="yaml-variant">

#### TABULAR {#facility_inputs-tabular}

*Generic tabular (CSV) facility model.*

</div>

<div className="yaml-variant">

#### COMPRESSOR_TABULAR {#facility_inputs-compressor_tabular}

*Tabular facility model for compressor energy functions.*

</div>

<div className="yaml-variant">

#### PUMP_CHART_SINGLE_SPEED {#facility_inputs-pump_chart_single_speed}

*Pump chart for a single-speed pump.*

```yaml
HEAD_MARGIN: <head_margin>
UNITS:
  RATE: <rate>
  HEAD: <head>
  EFFICIENCY: <efficiency>
```

- **HEAD_MARGIN**<span id="facility_inputs-pump_chart_single_speed-head_margin"></span><br/>  Adjustment of the head margin for power calibration. (<code>number</code> · default: <code>0.0</code>)

- **UNITS**<span id="facility_inputs-pump_chart_single_speed-units"></span><br/>  Defines the units (<code>Units</code>)
  - **RATE**<span id="facility_inputs-pump_chart_single_speed-units-rate"></span><br/>    Unit for rate in chart. Currently only AM3_PER_HOUR is supported (<code>AM3_PER_HOUR</code> · default: <code>AM3_PER_HOUR</code>)

  - **HEAD**<span id="facility_inputs-pump_chart_single_speed-units-head"></span><br/>    Unit for head in chart. (<code>M, KJ_PER_KG, JOULE_PER_KG</code> · default: <code>M</code>)

  - **EFFICIENCY**<span id="facility_inputs-pump_chart_single_speed-units-efficiency"></span><br/>    Unit of efficiency in chart. (<code>FRACTION, PERCENTAGE</code> · default: <code>PERCENTAGE</code>)


</div>

<div className="yaml-variant">

#### PUMP_CHART_VARIABLE_SPEED {#facility_inputs-pump_chart_variable_speed}

*Pump chart for a variable-speed pump.*

```yaml
HEAD_MARGIN: <head_margin>
UNITS:
  RATE: <rate>
  HEAD: <head>
  EFFICIENCY: <efficiency>
```

- **HEAD_MARGIN**<span id="facility_inputs-pump_chart_variable_speed-head_margin"></span><br/>  Adjustment of the head margin for power calibration. (<code>number</code> · default: <code>0.0</code>)

- **UNITS**<span id="facility_inputs-pump_chart_variable_speed-units"></span><br/>  Defines the units (<code>Units</code>)
  - **RATE**<span id="facility_inputs-pump_chart_variable_speed-units-rate"></span><br/>    Unit for rate in chart. Currently only AM3_PER_HOUR is supported (<code>AM3_PER_HOUR</code> · default: <code>AM3_PER_HOUR</code>)

  - **HEAD**<span id="facility_inputs-pump_chart_variable_speed-units-head"></span><br/>    Unit for head in chart. (<code>M, KJ_PER_KG, JOULE_PER_KG</code> · default: <code>M</code>)

  - **EFFICIENCY**<span id="facility_inputs-pump_chart_variable_speed-units-efficiency"></span><br/>    Unit of efficiency in chart. (<code>FRACTION, PERCENTAGE</code> · default: <code>PERCENTAGE</code>)


</div>

### NAME *(required)* {#facility_inputs-name}

Name of the facility input. (<code>text</code>)

### FILE *(required)* {#facility_inputs-file}

Specifies the name of an input file. (<code>text</code>)

---

## MODELS {#models}

Defines input files which characterize various facility elements.

```yaml
MODELS:
  - TYPE: <type>
    NAME: <name>
```

### TYPE *(required)* {#models-type}

The type of the component

Allowed values: `COMPRESSOR_CHART` &#124; `COMPRESSOR_WITH_TURBINE` &#124; `FLUID` &#124; `TURBINE` &#124; `VARIABLE_SPEED_COMPRESSOR_TRAIN` &#124; `SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN` &#124; `SINGLE_SPEED_COMPRESSOR_TRAIN` &#124; `VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES`

<div className="yaml-variant">

#### COMPRESSOR_CHART {#models-compressor_chart}

```yaml
TYPE: <type>
NAME: <name>
UNITS:
  RATE: <rate>
  HEAD: <head>
  EFFICIENCY: <efficiency>
```

- **TYPE** *(required)*<span id="models-compressor_chart-type"></span><br/>  The type of the component
  - **SINGLE_SPEED**<span id="models-compressor_chart-single_speed"></span>
    - **CURVE** *(required)*<span id="models-compressor_chart-single_speed-curve"></span><br/>      One single compressor chart curve.<br/>      Allowed values: <code>Curve ∣ File</code>
      - **FILE** *(required)*<span id="models-compressor_chart-single_speed-curve-file"></span><br/>        Specifies the name of an input file. See documentation for more information. (<code>text</code>)



  - **VARIABLE_SPEED**<span id="models-compressor_chart-variable_speed"></span>
    - **CURVES** *(required)*<span id="models-compressor_chart-variable_speed-curves"></span><br/>      Compressor chart curves, one per speed.<br/>      Allowed values: <code>list[Curve] ∣ File</code>
      - **FILE** *(required)*<span id="models-compressor_chart-variable_speed-curves-file"></span><br/>        Specifies the name of an input file. See documentation for more information. (<code>text</code>)



  - **GENERIC_FROM_DESIGN_POINT**<span id="models-compressor_chart-generic_from_design_point"></span>
    - **POLYTROPIC_EFFICIENCY** *(required)*<span id="models-compressor_chart-generic_from_design_point-polytropic_efficiency"></span><br/>      Polytropic efficiency for compressor chart (<code>number</code>)

    - **DESIGN_RATE** *(required)*<span id="models-compressor_chart-generic_from_design_point-design_rate"></span><br/>      Design rate for generic compressor chart (<code>number</code>)

    - **DESIGN_HEAD** *(required)*<span id="models-compressor_chart-generic_from_design_point-design_head"></span><br/>      Design head for generic compressor chart (<code>number</code>)


  - **GENERIC_FROM_INPUT**<span id="models-compressor_chart-generic_from_input"></span>
    - **POLYTROPIC_EFFICIENCY** *(required)*<span id="models-compressor_chart-generic_from_input-polytropic_efficiency"></span><br/>      Polytropic efficiency for compressor chart (<code>number</code>)



- **NAME** *(required)*<span id="models-compressor_chart-name"></span><br/>  Name of the model. See documentation for more information. (<code>text</code>)

- **UNITS**<span id="models-compressor_chart-units"></span><br/>  Defines the units (<code>Units</code>)
  - **RATE**<span id="models-compressor_chart-units-rate"></span><br/>    Unit for rate in chart. Currently only AM3_PER_HOUR is supported (<code>AM3_PER_HOUR</code> · default: <code>AM3_PER_HOUR</code>)

  - **HEAD**<span id="models-compressor_chart-units-head"></span><br/>    Unit for head in chart. (<code>M, KJ_PER_KG, JOULE_PER_KG</code> · default: <code>M</code>)

  - **EFFICIENCY**<span id="models-compressor_chart-units-efficiency"></span><br/>    Unit of efficiency in chart. (<code>FRACTION, PERCENTAGE</code> · default: <code>PERCENTAGE</code>)


</div>

<div className="yaml-variant">

#### COMPRESSOR_WITH_TURBINE {#models-compressor_with_turbine}

*Compressor driven by a gas turbine.*

```yaml
COMPRESSOR_MODEL: <compressor_model>
POWER_ADJUSTMENT_CONSTANT: <power_adjustment_constant>
POWER_ADJUSTMENT_FACTOR: <power_adjustment_factor>
TURBINE_MODEL: <turbine_model>
```

- **COMPRESSOR_MODEL** *(required)*<span id="models-compressor_with_turbine-compressor_model"></span><br/>  Reference to a compressor model (<code>text</code>)

- **POWER_ADJUSTMENT_CONSTANT**<span id="models-compressor_with_turbine-power_adjustment_constant"></span><br/>  Constant to adjust power usage in MW (<code>number</code> · default: <code>0.0</code>)

- **POWER_ADJUSTMENT_FACTOR**<span id="models-compressor_with_turbine-power_adjustment_factor"></span><br/>  Factor to adjust power usage in MW (<code>number</code> · default: <code>1.0</code>)

- **TURBINE_MODEL** *(required)*<span id="models-compressor_with_turbine-turbine_model"></span><br/>  Reference to a turbine model (<code>text</code>)

</div>

<div className="yaml-variant">

#### FLUID {#models-fluid}

*Fluid model using a predefined fluid type.*

```yaml
TYPE: <type>
EOS_MODEL: <eos_model>
FLUID_MODEL_TYPE: <fluid_model_type>
NAME: <name>
```

- **TYPE** *(required)*<span id="models-fluid-type"></span><br/>  The type of the component (<code>PREDEFINED, COMPOSITION</code>)

- **EOS_MODEL**<span id="models-fluid-eos_model"></span><br/>  Equation of state model. Supported models are SRK, PR, GERG_SRK, GERG_PR (<code>SRK, PR, GERG_SRK, GERG_PR</code> · default: <code>SRK</code>)

- **FLUID_MODEL_TYPE**<span id="models-fluid-fluid_model_type"></span><br/>  Defines the fluid model type. (default: <code>PREDEFINED</code>)
  - **PREDEFINED**<span id="models-fluid-predefined"></span><br/>    *Fluid model using a predefined fluid type.*
    - **GAS_TYPE**<span id="models-fluid-predefined-gas_type"></span><br/>      Predefined gas type. Supported types are ULTRA_DRY, DRY, MEDIUM, RICH, ULTRA_RICH (<code>ULTRA_DRY, DRY, MEDIUM, RICH, ULTRA_RICH</code>)


  - **COMPOSITION**<span id="models-fluid-composition"></span><br/>    *Fluid model defined by a custom composition.*
    - **COMPOSITION** *(required)*<span id="models-fluid-composition-composition"></span><br/>      Components in fluid and amount (relative to the others) in mole weights (<code>Composition</code>)
      - **CO2**<span id="models-fluid-composition-composition-co2"></span><br/>        Mole fraction of CO2 (<code>number</code> · default: <code>0.0</code>)

      - **ethane**<span id="models-fluid-composition-composition-ethane"></span><br/>        Mole fraction of ethane (<code>number</code> · default: <code>0.0</code>)

      - **i_butane**<span id="models-fluid-composition-composition-i_butane"></span><br/>        Mole fraction of i-butane (<code>number</code> · default: <code>0.0</code>)

      - **i_pentane**<span id="models-fluid-composition-composition-i_pentane"></span><br/>        Mole fraction of i-pentane (<code>number</code> · default: <code>0.0</code>)

      - **methane** *(required)*<span id="models-fluid-composition-composition-methane"></span><br/>        Mole fraction of methane (required) (<code>number</code>)

      - **n_butane**<span id="models-fluid-composition-composition-n_butane"></span><br/>        Mole fraction of n-butane (<code>number</code> · default: <code>0.0</code>)

      - **n_hexane**<span id="models-fluid-composition-composition-n_hexane"></span><br/>        Mole fraction of n-hexane (<code>number</code> · default: <code>0.0</code>)

      - **n_pentane**<span id="models-fluid-composition-composition-n_pentane"></span><br/>        Mole fraction of n-pentane (<code>number</code> · default: <code>0.0</code>)

      - **nitrogen**<span id="models-fluid-composition-composition-nitrogen"></span><br/>        Mole fraction of nitrogen (<code>number</code> · default: <code>0.0</code>)

      - **propane**<span id="models-fluid-composition-composition-propane"></span><br/>        Mole fraction of propane (<code>number</code> · default: <code>0.0</code>)

      - **water**<span id="models-fluid-composition-composition-water"></span><br/>        Mole fraction of water (<code>number</code> · default: <code>0.0</code>)




- **NAME** *(required)*<span id="models-fluid-name"></span><br/>  Name of the model. See documentation for more information. (<code>text</code>)

</div>

<div className="yaml-variant">

#### TURBINE {#models-turbine}

*Gas turbine with load-dependent efficiency curve.*

```yaml
LOWER_HEATING_VALUE: <lower_heating_value>
TURBINE_LOADS: <turbine_loads>
TURBINE_EFFICIENCIES: <turbine_efficiencies>
POWER_ADJUSTMENT_CONSTANT: <power_adjustment_constant>
POWER_ADJUSTMENT_FACTOR: <power_adjustment_factor>
```

- **LOWER_HEATING_VALUE** *(required)*<span id="models-turbine-lower_heating_value"></span><br/>  Lower heating value [MJ/Sm3] of fuel. Lower heating value is also known as net calorific value (<code>number</code>)

- **TURBINE_LOADS** *(required)*<span id="models-turbine-turbine_loads"></span><br/>  Load values [MW] in load vs efficiency table for turbine. Number of elements must correspond to number of elements in TURBINE_EFFICIENCIES. See documentation for more information. (<code>list[number]</code>)

- **TURBINE_EFFICIENCIES** *(required)*<span id="models-turbine-turbine_efficiencies"></span><br/>  Efficiency values in load vs efficiency table for turbine. Efficiency is given as fraction between 0 and 1 corresponding to 0-100%. Number of elements must correspond to number of elements in TURBINE_LOADS. See documentation for more information. (<code>list[number]</code>)

- **POWER_ADJUSTMENT_CONSTANT**<span id="models-turbine-power_adjustment_constant"></span><br/>  Constant to adjust power usage in MW (<code>number</code> · default: <code>0</code>)

- **POWER_ADJUSTMENT_FACTOR**<span id="models-turbine-power_adjustment_factor"></span><br/>  Factor to adjust power usage in MW (<code>number</code> · default: <code>1.0</code>)

</div>

<div className="yaml-variant">

#### VARIABLE_SPEED_COMPRESSOR_TRAIN {#models-variable_speed_compressor_train}

*Variable-speed compressor train where RPM adjusts to match operating conditions.*

```yaml
MAXIMUM_POWER: <maximum_power>
COMPRESSOR_TRAIN:
  STAGES:
    - INLET_TEMPERATURE: <inlet_temperature>
      COMPRESSOR_CHART: <compressor_chart>
      PRESSURE_DROP_AHEAD_OF_STAGE: <pressure_drop_ahead_of_stage>
      CONTROL_MARGIN: <control_margin>
      CONTROL_MARGIN_UNIT: <control_margin_unit>
PRESSURE_CONTROL: <pressure_control>
CALCULATE_MAX_RATE: <calculate_max_rate>
POWER_ADJUSTMENT_CONSTANT: <power_adjustment_constant>
POWER_ADJUSTMENT_FACTOR: <power_adjustment_factor>
FLUID_MODEL: <fluid_model>
```

- **MAXIMUM_POWER**<span id="models-variable_speed_compressor_train-maximum_power"></span><br/>  Optional constant MW maximum power the compressor train can require (<code>number</code>)

- **COMPRESSOR_TRAIN** *(required)*<span id="models-variable_speed_compressor_train-compressor_train"></span><br/>  Compressor train definition
  - **STAGES** *(required)*<span id="models-variable_speed_compressor_train-compressor_train-stages"></span><br/>    List of compressor stages
    - **INLET_TEMPERATURE** *(required)*<span id="models-variable_speed_compressor_train-compressor_train-stages-inlet_temperature"></span><br/>      Inlet temperature in Celsius for stage (<code>number</code>)

    - **COMPRESSOR_CHART** *(required)*<span id="models-variable_speed_compressor_train-compressor_train-stages-compressor_chart"></span><br/>      Reference to compressor chart model for stage, must be defined in MODELS or FACILITY_INPUTS (<code>text</code>)

    - **PRESSURE_DROP_AHEAD_OF_STAGE**<span id="models-variable_speed_compressor_train-compressor_train-stages-pressure_drop_ahead_of_stage"></span><br/>      Pressure drop before compression stage [in bar] (<code>number</code> · default: <code>0.0</code>)

    - **CONTROL_MARGIN** *(required)*<span id="models-variable_speed_compressor_train-compressor_train-stages-control_margin"></span><br/>      Surge control margin, see documentation for more details. (<code>number</code>)

    - **CONTROL_MARGIN_UNIT** *(required)*<span id="models-variable_speed_compressor_train-compressor_train-stages-control_margin_unit"></span><br/>      The unit of the surge control margin. (<code>FRACTION, PERCENTAGE</code>)



- **PRESSURE_CONTROL**<span id="models-variable_speed_compressor_train-pressure_control"></span><br/>  Method for pressure control (<code>DOWNSTREAM_CHOKE, UPSTREAM_CHOKE, INDIVIDUAL_ASV_PRESSURE, INDIVIDUAL_ASV_RATE, COMMON_ASV</code> · default: <code>DOWNSTREAM_CHOKE</code>)

- **CALCULATE_MAX_RATE**<span id="models-variable_speed_compressor_train-calculate_max_rate"></span><br/>  Optional compressor train max standard rate [Sm3/day] in result if set to true. Default false. Use with caution. This will increase runtime significantly. (<code>true / false</code> · default: <code>False</code>)

- **POWER_ADJUSTMENT_CONSTANT**<span id="models-variable_speed_compressor_train-power_adjustment_constant"></span><br/>  Constant to adjust power usage in MW (<code>number</code> · default: <code>0.0</code>)

- **POWER_ADJUSTMENT_FACTOR**<span id="models-variable_speed_compressor_train-power_adjustment_factor"></span><br/>  Factor to adjust power usage in MW (<code>number</code> · default: <code>1.0</code>)

- **FLUID_MODEL** *(required)*<span id="models-variable_speed_compressor_train-fluid_model"></span><br/>  Reference to a fluid model (<code>text</code>)

</div>

<div className="yaml-variant">

#### SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN {#models-simplified_variable_speed_compressor_train}

*Simplified variable-speed compressor train using generic charts.*

```yaml
MAXIMUM_POWER: <maximum_power>
COMPRESSOR_TRAIN:
  STAGES:
    - INLET_TEMPERATURE: <inlet_temperature>
      COMPRESSOR_CHART: <compressor_chart>
  MAXIMUM_PRESSURE_RATIO_PER_STAGE: <maximum_pressure_ratio_per_stage>
  INLET_TEMPERATURE: <inlet_temperature>
  COMPRESSOR_CHART: <compressor_chart>
CALCULATE_MAX_RATE: <calculate_max_rate>
FLUID_MODEL: <fluid_model>
POWER_ADJUSTMENT_CONSTANT: <power_adjustment_constant>
POWER_ADJUSTMENT_FACTOR: <power_adjustment_factor>
```

- **MAXIMUM_POWER**<span id="models-simplified_variable_speed_compressor_train-maximum_power"></span><br/>  Optional constant MW maximum power the compressor train can require (<code>number</code>)

- **COMPRESSOR_TRAIN** *(required)*<span id="models-simplified_variable_speed_compressor_train-compressor_train"></span><br/>  Compressor train definition
  - **STAGES** *(required)*<span id="models-simplified_variable_speed_compressor_train-compressor_train-stages"></span><br/>    List of compressor stages
    - **INLET_TEMPERATURE** *(required)*<span id="models-simplified_variable_speed_compressor_train-compressor_train-stages-inlet_temperature"></span><br/>      Inlet temperature in Celsius for stage (<code>number</code>)

    - **COMPRESSOR_CHART** *(required)*<span id="models-simplified_variable_speed_compressor_train-compressor_train-stages-compressor_chart"></span><br/>      Reference to compressor chart model for stage, must be defined in MODELS or FACILITY_INPUTS (<code>text</code>)


  - **MAXIMUM_PRESSURE_RATIO_PER_STAGE**<span id="models-simplified_variable_speed_compressor_train-compressor_train-maximum_pressure_ratio_per_stage"></span><br/>    Maximum pressure ratio per stage. Number of compressors will be large enough to ensure no pressure ratios are above a given maximum pressure ratio per stage, but not larger (<code>number</code>)

  - **INLET_TEMPERATURE** *(required)*<span id="models-simplified_variable_speed_compressor_train-compressor_train-inlet_temperature"></span><br/>    Inlet temperature in Celsius for stage (<code>number</code>)

  - **COMPRESSOR_CHART** *(required)*<span id="models-simplified_variable_speed_compressor_train-compressor_train-compressor_chart"></span><br/>    Reference to compressor chart model for stage, must be defined in MODELS or FACILITY_INPUTS (<code>text</code>)


- **CALCULATE_MAX_RATE**<span id="models-simplified_variable_speed_compressor_train-calculate_max_rate"></span><br/>  Optional compressor train max standard rate [Sm3/day] in result if set to true. Default false. Use with caution. This will increase runtime significantly. (<code>true / false</code> · default: <code>False</code>)

- **FLUID_MODEL** *(required)*<span id="models-simplified_variable_speed_compressor_train-fluid_model"></span><br/>  Reference to a fluid model (<code>text</code>)

- **POWER_ADJUSTMENT_CONSTANT**<span id="models-simplified_variable_speed_compressor_train-power_adjustment_constant"></span><br/>  Constant to adjust power usage in MW (<code>number</code> · default: <code>0.0</code>)

- **POWER_ADJUSTMENT_FACTOR**<span id="models-simplified_variable_speed_compressor_train-power_adjustment_factor"></span><br/>  Factor to adjust power usage in MW (<code>number</code> · default: <code>1.0</code>)

</div>

<div className="yaml-variant">

#### SINGLE_SPEED_COMPRESSOR_TRAIN {#models-single_speed_compressor_train}

*Single-speed compressor train with fixed RPM.*

```yaml
MAXIMUM_POWER: <maximum_power>
COMPRESSOR_TRAIN:
  STAGES:
    - INLET_TEMPERATURE: <inlet_temperature>
      COMPRESSOR_CHART: <compressor_chart>
      PRESSURE_DROP_AHEAD_OF_STAGE: <pressure_drop_ahead_of_stage>
      CONTROL_MARGIN: <control_margin>
      CONTROL_MARGIN_UNIT: <control_margin_unit>
PRESSURE_CONTROL: <pressure_control>
MAXIMUM_DISCHARGE_PRESSURE: <maximum_discharge_pressure>
CALCULATE_MAX_RATE: <calculate_max_rate>
POWER_ADJUSTMENT_CONSTANT: <power_adjustment_constant>
POWER_ADJUSTMENT_FACTOR: <power_adjustment_factor>
FLUID_MODEL: <fluid_model>
```

- **MAXIMUM_POWER**<span id="models-single_speed_compressor_train-maximum_power"></span><br/>  Optional constant MW maximum power the compressor train can require (<code>number</code>)

- **COMPRESSOR_TRAIN** *(required)*<span id="models-single_speed_compressor_train-compressor_train"></span><br/>  Compressor train definition
  - **STAGES** *(required)*<span id="models-single_speed_compressor_train-compressor_train-stages"></span><br/>    List of compressor stages
    - **INLET_TEMPERATURE** *(required)*<span id="models-single_speed_compressor_train-compressor_train-stages-inlet_temperature"></span><br/>      Inlet temperature in Celsius for stage (<code>number</code>)

    - **COMPRESSOR_CHART** *(required)*<span id="models-single_speed_compressor_train-compressor_train-stages-compressor_chart"></span><br/>      Reference to compressor chart model for stage, must be defined in MODELS or FACILITY_INPUTS (<code>text</code>)

    - **PRESSURE_DROP_AHEAD_OF_STAGE**<span id="models-single_speed_compressor_train-compressor_train-stages-pressure_drop_ahead_of_stage"></span><br/>      Pressure drop before compression stage [in bar] (<code>number</code> · default: <code>0.0</code>)

    - **CONTROL_MARGIN** *(required)*<span id="models-single_speed_compressor_train-compressor_train-stages-control_margin"></span><br/>      Surge control margin, see documentation for more details. (<code>number</code>)

    - **CONTROL_MARGIN_UNIT** *(required)*<span id="models-single_speed_compressor_train-compressor_train-stages-control_margin_unit"></span><br/>      The unit of the surge control margin. (<code>FRACTION, PERCENTAGE</code>)



- **PRESSURE_CONTROL**<span id="models-single_speed_compressor_train-pressure_control"></span><br/>  Method for pressure control (<code>DOWNSTREAM_CHOKE, UPSTREAM_CHOKE, INDIVIDUAL_ASV_PRESSURE, INDIVIDUAL_ASV_RATE, COMMON_ASV</code> · default: <code>DOWNSTREAM_CHOKE</code>)

- **MAXIMUM_DISCHARGE_PRESSURE**<span id="models-single_speed_compressor_train-maximum_discharge_pressure"></span><br/>  Maximum discharge pressure in bar (can only use if pressure control is DOWNSTREAM_CHOKE) (<code>number</code>)

- **CALCULATE_MAX_RATE**<span id="models-single_speed_compressor_train-calculate_max_rate"></span><br/>  Optional compressor train max standard rate [Sm3/day] in result if set to true. Default false. Use with caution. This will increase runtime significantly. (<code>true / false</code> · default: <code>False</code>)

- **POWER_ADJUSTMENT_CONSTANT**<span id="models-single_speed_compressor_train-power_adjustment_constant"></span><br/>  Constant to adjust power usage in MW (<code>number</code> · default: <code>0.0</code>)

- **POWER_ADJUSTMENT_FACTOR**<span id="models-single_speed_compressor_train-power_adjustment_factor"></span><br/>  Factor to adjust power usage in MW (<code>number</code> · default: <code>1.0</code>)

- **FLUID_MODEL** *(required)*<span id="models-single_speed_compressor_train-fluid_model"></span><br/>  Reference to a fluid model (<code>text</code>)

</div>

<div className="yaml-variant">

#### VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES {#models-variable_speed_compressor_train_multiple_streams_and_pressures}

*Variable-speed compressor train with multiple inlet/outlet streams and interstage pressures.*

```yaml
MAXIMUM_POWER: <maximum_power>
STREAMS:
  - TYPE: <type>
    NAME: <name>
STAGES:
  - INLET_TEMPERATURE: <inlet_temperature>
    COMPRESSOR_CHART: <compressor_chart>
    PRESSURE_DROP_AHEAD_OF_STAGE: <pressure_drop_ahead_of_stage>
    CONTROL_MARGIN: <control_margin>
    CONTROL_MARGIN_UNIT: <control_margin_unit>
    STREAM: <stream>
    INTERSTAGE_CONTROL_PRESSURE:
      UPSTREAM_PRESSURE_CONTROL: <upstream_pressure_control>
      DOWNSTREAM_PRESSURE_CONTROL: <downstream_pressure_control>
PRESSURE_CONTROL: <pressure_control>
POWER_ADJUSTMENT_CONSTANT: <power_adjustment_constant>
POWER_ADJUSTMENT_FACTOR: <power_adjustment_factor>
```

- **MAXIMUM_POWER**<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-maximum_power"></span><br/>  Optional constant MW maximum power the compressor train can require (<code>number</code>)

- **STREAMS** *(required)*<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-streams"></span><br/>  A list of all in- and out-going streams for the compressor train. The same equation of state (EOS) must be used for each INGOING stream fluid models
  - **TYPE** *(required)*<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-streams-type"></span><br/>    The type of the component
    - **INGOING**<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-streams-ingoing"></span><br/>      *Ingoing fluid stream.*
      - **FLUID_MODEL** *(required)*<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-streams-ingoing-fluid_model"></span><br/>        Reference to a fluid model (<code>text</code>)


    - **OUTGOING**<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-streams-outgoing"></span><br/>      *Outgoing stream — no fluid model needed.*


  - **NAME** *(required)*<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-streams-name"></span><br/>    Name of the ingoing fluid stream (<code>text</code>)


- **STAGES** *(required)*<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-stages"></span><br/>  A list of all stages in compressor model.
  - **INLET_TEMPERATURE** *(required)*<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-stages-inlet_temperature"></span><br/>    Inlet temperature in Celsius for stage (<code>number</code>)

  - **COMPRESSOR_CHART** *(required)*<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-stages-compressor_chart"></span><br/>    Reference to compressor chart model for stage, must be defined in MODELS or FACILITY_INPUTS (<code>text</code>)

  - **PRESSURE_DROP_AHEAD_OF_STAGE**<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-stages-pressure_drop_ahead_of_stage"></span><br/>    Pressure drop before compression stage [in bar] (<code>number</code> · default: <code>0.0</code>)

  - **CONTROL_MARGIN** *(required)*<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-stages-control_margin"></span><br/>    Surge control margin, see documentation for more details. (<code>number</code>)

  - **CONTROL_MARGIN_UNIT** *(required)*<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-stages-control_margin_unit"></span><br/>    The unit of the surge control margin. (<code>FRACTION, PERCENTAGE</code>)

  - **STREAM**<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-stages-stream"></span><br/>    Reference to stream from STREAMS. (<code>list[text]</code>)

  - **INTERSTAGE_CONTROL_PRESSURE**<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-stages-interstage_control_pressure"></span><br/>    Pressure control. Can only be specified for one (only one) of the stages 2, ..., N.
    - **UPSTREAM_PRESSURE_CONTROL** *(required)*<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-stages-interstage_control_pressure-upstream_pressure_control"></span><br/>      Pressure control. (<code>DOWNSTREAM_CHOKE, UPSTREAM_CHOKE, INDIVIDUAL_ASV_PRESSURE, INDIVIDUAL_ASV_RATE, COMMON_ASV</code>)

    - **DOWNSTREAM_PRESSURE_CONTROL** *(required)*<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-stages-interstage_control_pressure-downstream_pressure_control"></span><br/>      Pressure control. (<code>DOWNSTREAM_CHOKE, UPSTREAM_CHOKE, INDIVIDUAL_ASV_PRESSURE, INDIVIDUAL_ASV_RATE, COMMON_ASV</code>)



- **PRESSURE_CONTROL**<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-pressure_control"></span><br/>  Method for pressure control (<code>DOWNSTREAM_CHOKE, UPSTREAM_CHOKE, INDIVIDUAL_ASV_PRESSURE, INDIVIDUAL_ASV_RATE, COMMON_ASV</code> · default: <code>DOWNSTREAM_CHOKE</code>)

- **POWER_ADJUSTMENT_CONSTANT**<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-power_adjustment_constant"></span><br/>  Constant to adjust power usage in MW (<code>number</code> · default: <code>0.0</code>)

- **POWER_ADJUSTMENT_FACTOR**<span id="models-variable_speed_compressor_train_multiple_streams_and_pressures-power_adjustment_factor"></span><br/>  Factor to adjust power usage in MW (<code>number</code> · default: <code>1.0</code>)

</div>

### NAME *(required)* {#models-name}

Name of the model. See documentation for more information. (<code>text</code>)

---

## FUEL_TYPES *(required)* {#fuel_types}

Specifies the various fuel types and associated emissions used in the model.

```yaml
FUEL_TYPES:
  - NAME: <name>
    CATEGORY: <category>
    EMISSIONS:
      - NAME: <name>
        FACTOR: <factor>
    LOWER_HEATING_VALUE: <lower_heating_value>
```

### NAME *(required)* {#fuel_types-name}

Name of the fuel. (<code>text</code>)

### CATEGORY {#fuel_types-category}

Output category/tag. (<code>FUEL-GAS, DIESEL</code>)

### EMISSIONS *(required)* {#fuel_types-emissions}

Emission types and their attributes for this fuel. (<code>list[Emission]</code>)

- **NAME** *(required)*<span id="fuel_types-emissions-name"></span><br/>  Name of the emission. (<code>text</code>)

- **FACTOR** *(required)*<span id="fuel_types-emissions-factor"></span><br/>  Emission factor for fuel in kg emission/Sm3 fuel. May be a constant number or an expression using vectors from a time series input.<br/>  Allowed values: <code>text ∣ number ∣ integer</code>

### LOWER_HEATING_VALUE {#fuel_types-lower_heating_value}

Warning! Deprecated. Does not have any effect. Lower heating value [MJ/Sm3] of fuel. Lower heating value is also known as net calorific value (<code>number</code>)

---

## VARIABLES {#variables}

Defines variables used in an energy usage model by means of expressions or constants.

```yaml
VARIABLES:
  <name>:
```

---

## INSTALLATIONS *(required)* {#installations}

<code>list[Installation]</code>

Description of the system of energy consumers.

```yaml
INSTALLATIONS:
  - NAME: <name>
    CATEGORY: <category>
    HCEXPORT: <hcexport>
    FUEL: <fuel>
    REGULARITY: <regularity>
    GENERATORSETS:
      - NAME: <name>
        CATEGORY: <category>
        FUEL: <fuel>
        ELECTRICITY2FUEL: <electricity2fuel>
        CABLE_LOSS: <cable_loss>
        MAX_USAGE_FROM_SHORE: <max_usage_from_shore>
        CONSUMERS:
          - Type: <type>
            NAME: <name>
            CATEGORY: <category>
            ENERGY_USAGE_MODEL:
              TYPE: <type>
              CONDITION: <condition>
              CONDITIONS: <conditions>
    FUELCONSUMERS:
      - Type: <type>
        NAME: <name>
        CATEGORY: <category>
        ENERGY_USAGE_MODEL:
          TYPE: <type>
          CONDITION: <condition>
          CONDITIONS: <conditions>
        FUEL: <fuel>
    VENTING_EMITTERS:
      - TYPE: <type>
        NAME: <name>
        CATEGORY: <category>
```

### NAME *(required)* {#installations-name}

Name of the installation. (<code>text</code>)

### CATEGORY {#installations-category}

Output category/tag. (<code>FIXED, MOBILE</code>)

### HCEXPORT {#installations-hcexport}

Defines the export of hydrocarbons as number of oil equivalents in Sm3.

<code>text ∣ number ∣ integer ∣ dict[datetime, text ∣ number ∣ integer]</code> · default: <code>0</code>

### FUEL {#installations-fuel}

Main fuel type for installation. (<code>text ∣ dict[datetime, text]</code>)

### REGULARITY {#installations-regularity}

Regularity of the installation can be specified by a single number or as an expression. USE WITH CARE.

<code>text ∣ number ∣ integer ∣ dict[datetime, text ∣ number ∣ integer]</code> · default: <code>1</code>

### GENERATORSETS {#installations-generatorsets}

Defines one or more generator sets.

- **NAME** *(required)*<span id="installations-generatorsets-name"></span><br/>  Name of the generator set. (<code>text</code>)

- **CATEGORY** *(required)*<span id="installations-generatorsets-category"></span><br/>  Output category/tag.<br/>  Allowed values: <code>BASE-LOAD, COLD-VENTING-FUGITIVE, COMPRESSOR, FIXED-PRODUCTION-LOAD, FLARE, MISCELLANEOUS, PUMP, GAS-DRIVEN-COMPRESSOR, TURBINE-GENERATOR, POWER-FROM-SHORE, OFFSHORE-WIND, LOADING, STORAGE, STEAM-TURBINE-GENERATOR, BOILER, HEATER ∣ dict[datetime, BASE-LOAD, COLD-VENTING-FUGITIVE, COMPRESSOR, FIXED-PRODUCTION-LOAD, FLARE, MISCELLANEOUS, PUMP, GAS-DRIVEN-COMPRESSOR, TURBINE-GENERATOR, POWER-FROM-SHORE, OFFSHORE-WIND, LOADING, STORAGE, STEAM-TURBINE-GENERATOR, BOILER, HEATER]</code>

- **FUEL**<span id="installations-generatorsets-fuel"></span><br/>  The fuel used by the generator set.<br/>  Allowed values: <code>text ∣ dict[datetime, text]</code>

- **ELECTRICITY2FUEL** *(required)*<span id="installations-generatorsets-electricity2fuel"></span><br/>  Specifies the correlation between the electric power delivered and the fuel burned by a generator set.<br/>  Allowed values: <code>text ∣ dict[datetime, text]</code>

- **CABLE_LOSS**<span id="installations-generatorsets-cable_loss"></span><br/>  Cable loss from shore, fraction of from shore consumption<br/>  Allowed values: <code>text ∣ number ∣ integer</code>

- **MAX_USAGE_FROM_SHORE**<span id="installations-generatorsets-max_usage_from_shore"></span><br/>  The peak load/effect that is expected for one hour, per year (MW)<br/>  Allowed values: <code>text ∣ number ∣ integer</code>

- **CONSUMERS** *(required)*<span id="installations-generatorsets-consumers"></span><br/>  Consumers getting electrical power from the generator set. (<code>list[ELECTRICITY_CONSUMER]</code>)
  - **Type**<span id="installations-generatorsets-consumers-type"></span><br/>    The type of the component (<code>ELECTRICITY_CONSUMER</code> · default: <code>ELECTRICITY_CONSUMER</code>)

  - **NAME** *(required)*<span id="installations-generatorsets-consumers-name"></span><br/>    Name of the consumer. (<code>text</code>)

  - **CATEGORY** *(required)*<span id="installations-generatorsets-consumers-category"></span><br/>    Output category/tag.<br/>    Allowed values: <code>BASE-LOAD, COLD-VENTING-FUGITIVE, COMPRESSOR, FIXED-PRODUCTION-LOAD, FLARE, MISCELLANEOUS, PUMP, GAS-DRIVEN-COMPRESSOR, TURBINE-GENERATOR, POWER-FROM-SHORE, OFFSHORE-WIND, LOADING, STORAGE, STEAM-TURBINE-GENERATOR, BOILER, HEATER ∣ dict[datetime, BASE-LOAD, COLD-VENTING-FUGITIVE, COMPRESSOR, FIXED-PRODUCTION-LOAD, FLARE, MISCELLANEOUS, PUMP, GAS-DRIVEN-COMPRESSOR, TURBINE-GENERATOR, POWER-FROM-SHORE, OFFSHORE-WIND, LOADING, STORAGE, STEAM-TURBINE-GENERATOR, BOILER, HEATER]</code>

  - **ENERGY_USAGE_MODEL** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model"></span><br/>    Definition of the energy usage model for the consumer.
    - **TYPE** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-type"></span><br/>      The type of the component
      - **DIRECT**<span id="installations-generatorsets-consumers-energy_usage_model-direct"></span><br/>        *Direct electrical load.*
        - **POWERLOSSFACTOR**<span id="installations-generatorsets-consumers-energy_usage_model-direct-powerlossfactor"></span><br/>          A factor that may be added to account for power line losses.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **CONSUMPTION_RATE_TYPE**<span id="installations-generatorsets-consumers-energy_usage_model-direct-consumption_rate_type"></span><br/>          Defines the energy usage rate as stream day or calendar day. (<code>STREAM_DAY, CALENDAR_DAY</code>)

        - **LOAD** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-direct-load"></span><br/>          Fixed power consumer with constant load.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>


      - **COMPRESSOR**<span id="installations-generatorsets-consumers-energy_usage_model-compressor"></span><br/>        *Single compressor energy model.*
        - **POWERLOSSFACTOR**<span id="installations-generatorsets-consumers-energy_usage_model-compressor-powerlossfactor"></span><br/>          A factor that may be added to account for power line losses.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **ENERGY_FUNCTION** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-compressor-energy_function"></span><br/>          The compressor energy function, reference to a compressor type facility model defined in FACILITY_INPUTS (<code>text</code>)

        - **RATE** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-compressor-rate"></span><br/>          Fluid (gas) rate through the compressor in Sm3/day<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **SUCTION_PRESSURE**<span id="installations-generatorsets-consumers-energy_usage_model-compressor-suction_pressure"></span><br/>          Fluid (gas) pressure at compressor inlet in bars<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **DISCHARGE_PRESSURE**<span id="installations-generatorsets-consumers-energy_usage_model-compressor-discharge_pressure"></span><br/>          Fluid (gas) pressure at compressor outlet in bars<br/>          Allowed values: <code>text ∣ number ∣ integer</code>


      - **PUMP**<span id="installations-generatorsets-consumers-energy_usage_model-pump"></span><br/>        *Single pump energy model.*
        - **POWERLOSSFACTOR**<span id="installations-generatorsets-consumers-energy_usage_model-pump-powerlossfactor"></span><br/>          A factor that may be added to account for power line losses.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **ENERGY_FUNCTION** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-pump-energy_function"></span><br/>          The pump energy function, reference to a pump type facility model defined in FACILITY_INPUTS (<code>text</code>)

        - **RATE**<span id="installations-generatorsets-consumers-energy_usage_model-pump-rate"></span><br/>          Fluid rate through the pump in Sm3/day<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **SUCTION_PRESSURE**<span id="installations-generatorsets-consumers-energy_usage_model-pump-suction_pressure"></span><br/>          Fluid pressure at pump inlet in bars<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **DISCHARGE_PRESSURE**<span id="installations-generatorsets-consumers-energy_usage_model-pump-discharge_pressure"></span><br/>          Fluid pressure at pump outlet in bars<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **FLUID_DENSITY** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-pump-fluid_density"></span><br/>          Density of the fluid in kg/m3.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>


      - **COMPRESSOR_SYSTEM**<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system"></span><br/>        *System of multiple compressors.*
        - **POWERLOSSFACTOR**<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-powerlossfactor"></span><br/>          A factor that may be added to account for power line losses.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **COMPRESSORS** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-compressors"></span><br/>          The compressors in a compressor system.
          - **NAME** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-compressors-name"></span><br/>            Name of the compressor (<code>text</code>)

          - **COMPRESSOR_MODEL** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-compressors-compressor_model"></span><br/>            Reference to a compressor type facility model defined in FACILITY_INPUTS (<code>text</code>)


        - **TOTAL_SYSTEM_RATE**<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-total_system_rate"></span><br/>          Total fluid rate through the system<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **OPERATIONAL_SETTINGS** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-operational_settings"></span><br/>          Operational settings of the system.
          - **CROSSOVER**<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-operational_settings-crossover"></span><br/>            Set cross over rules in system operational setting. (<code>list[integer]</code>)

          - **RATES**<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-operational_settings-rates"></span><br/>            Set rate per consumer in a consumer system operational setting.<br/>            Allowed values: <code>list[text ∣ number ∣ integer]</code>

          - **RATE_FRACTIONS**<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-operational_settings-rate_fractions"></span><br/>            List of expressions defining fractional rate (of total system rate) per consumer.<br/>            Allowed values: <code>list[text ∣ number ∣ integer]</code>

          - **SUCTION_PRESSURES**<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-operational_settings-suction_pressures"></span><br/>            Set suction pressure per consumer in a consumer system operational setting.<br/>            Allowed values: <code>list[text ∣ number ∣ integer]</code>

          - **DISCHARGE_PRESSURES**<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-operational_settings-discharge_pressures"></span><br/>            Set discharge pressure per consumer in a consumer system operational setting.<br/>            Allowed values: <code>list[text ∣ number ∣ integer]</code>

          - **DISCHARGE_PRESSURE**<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-operational_settings-discharge_pressure"></span><br/>            Set discharge pressure equal for all consumers in a consumer system operational setting.<br/>            Allowed values: <code>text ∣ number ∣ integer</code>

          - **SUCTION_PRESSURE**<span id="installations-generatorsets-consumers-energy_usage_model-compressor_system-operational_settings-suction_pressure"></span><br/>            Set suction pressure equal for all consumers in a consumer system operational setting.<br/>            Allowed values: <code>text ∣ number ∣ integer</code>



      - **PUMP_SYSTEM**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system"></span><br/>        *System of multiple pumps.*
        - **POWERLOSSFACTOR**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-powerlossfactor"></span><br/>          A factor that may be added to account for power line losses.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **PUMPS** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-pumps"></span><br/>          The pumps in a pump system.
          - **NAME** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-pumps-name"></span><br/>            Name of the pump (<code>text</code>)

          - **COMPRESSOR_MODEL** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-pumps-compressor_model"></span><br/>            Reference to a pump type facility model defined in FACILITY_INPUTS (<code>text</code>)


        - **FLUID_DENSITY**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-fluid_density"></span><br/>          Density of the fluid in kg/m3.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **TOTAL_SYSTEM_RATE**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-total_system_rate"></span><br/>          Total fluid rate through the system<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **OPERATIONAL_SETTINGS** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-operational_settings"></span><br/>          Operational settings of the system.
          - **CROSSOVER**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-operational_settings-crossover"></span><br/>            Set cross over rules in system operational setting. (<code>list[integer]</code>)

          - **RATES**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-operational_settings-rates"></span><br/>            Set rate per consumer in a consumer system operational setting.<br/>            Allowed values: <code>list[text ∣ number ∣ integer]</code>

          - **RATE_FRACTIONS**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-operational_settings-rate_fractions"></span><br/>            List of expressions defining fractional rate (of total system rate) per consumer.<br/>            Allowed values: <code>list[text ∣ number ∣ integer]</code>

          - **SUCTION_PRESSURES**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-operational_settings-suction_pressures"></span><br/>            Set suction pressure per consumer in a consumer system operational setting.<br/>            Allowed values: <code>list[text ∣ number ∣ integer]</code>

          - **DISCHARGE_PRESSURES**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-operational_settings-discharge_pressures"></span><br/>            Set discharge pressure per consumer in a consumer system operational setting.<br/>            Allowed values: <code>list[text ∣ number ∣ integer]</code>

          - **DISCHARGE_PRESSURE**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-operational_settings-discharge_pressure"></span><br/>            Set discharge pressure equal for all consumers in a consumer system operational setting.<br/>            Allowed values: <code>text ∣ number ∣ integer</code>

          - **SUCTION_PRESSURE**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-operational_settings-suction_pressure"></span><br/>            Set suction pressure equal for all consumers in a consumer system operational setting.<br/>            Allowed values: <code>text ∣ number ∣ integer</code>

          - **FLUID_DENSITIES**<span id="installations-generatorsets-consumers-energy_usage_model-pump_system-operational_settings-fluid_densities"></span><br/>            Set fluid density per consumer in a consumer system operational setting. Will overwrite the systems common fluid density expression<br/>            Allowed values: <code>list[text ∣ number ∣ integer]</code>



      - **TABULATED**<span id="installations-generatorsets-consumers-energy_usage_model-tabulated"></span><br/>        *Tabulated energy function.*
        - **POWERLOSSFACTOR**<span id="installations-generatorsets-consumers-energy_usage_model-tabulated-powerlossfactor"></span><br/>          A factor that may be added to account for power line losses.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **ENERGY_FUNCTION** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-tabulated-energy_function"></span><br/>          The tabulated energy function, reference to a tabular type facility model defined in FACILITY_INPUTS (<code>text</code>)

        - **VARIABLES** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-tabulated-variables"></span><br/>          Variables for the tabulated energy function
          - **NAME** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-tabulated-variables-name"></span><br/>            Name of variable. Must correspond exactly to header/column name in the energy function (<code>text</code>)

          - **EXPRESSION** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-tabulated-variables-expression"></span><br/>            Expression defining the variable<br/>            Allowed values: <code>text ∣ number ∣ integer</code>



      - **VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES**<span id="installations-generatorsets-consumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures"></span><br/>        *Variable-speed compressor train with multiple streams.*
        - **POWERLOSSFACTOR**<span id="installations-generatorsets-consumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-powerlossfactor"></span><br/>          A factor that may be added to account for power line losses.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **RATE_UNIT**<span id="installations-generatorsets-consumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-rate_unit"></span><br/>          Defaults to SM3_PER_DAY, only SM3_PER_DAY implemented for now (<code>SM3_PER_DAY</code> · default: <code>SM3_PER_DAY</code>)

        - **COMPRESSOR_TRAIN_MODEL** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-compressor_train_model"></span><br/>          The compressor train model, reference to a compressor type model defined in MODELS (<code>text</code>)

        - **RATE_PER_STREAM** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-rate_per_stream"></span><br/>          Fluid (gas) rate for each of the streams going into or out of the compressor train (excluding the outlet of the last compressor stage) in Sm3/day<br/>          Allowed values: <code>list[text ∣ number ∣ integer]</code>

        - **SUCTION_PRESSURE** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-suction_pressure"></span><br/>          Fluid (gas) pressure at compressor train inlet in bars<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **DISCHARGE_PRESSURE** *(required)*<span id="installations-generatorsets-consumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-discharge_pressure"></span><br/>          Fluid (gas) pressure at compressor train outlet in bars<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **INTERSTAGE_CONTROL_PRESSURE**<span id="installations-generatorsets-consumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-interstage_control_pressure"></span><br/>          Fluid (gas) pressure at an intermediate step in the compressor train<br/>          Allowed values: <code>text ∣ number ∣ integer</code>



    - **CONDITION**<span id="installations-generatorsets-consumers-energy_usage_model-condition"></span><br/>      Logical condition for the consumer to be used.<br/>      Allowed values: <code>text ∣ number ∣ integer</code>

    - **CONDITIONS**<span id="installations-generatorsets-consumers-energy_usage_model-conditions"></span><br/>      Logical conditions for the consumer to be used.<br/>      Allowed values: <code>list[text ∣ number ∣ integer]</code>



### FUELCONSUMERS {#installations-fuelconsumers}

Defines fuel consumers on the installation which are not generators. (<code>list[FUEL_CONSUMER]</code>)

- **Type**<span id="installations-fuelconsumers-type"></span><br/>  The type of the component (<code>FUEL_CONSUMER</code> · default: <code>FUEL_CONSUMER</code>)

- **NAME** *(required)*<span id="installations-fuelconsumers-name"></span><br/>  Name of the consumer. (<code>text</code>)

- **CATEGORY** *(required)*<span id="installations-fuelconsumers-category"></span><br/>  Output category/tag.<br/>  Allowed values: <code>BASE-LOAD, COLD-VENTING-FUGITIVE, COMPRESSOR, FIXED-PRODUCTION-LOAD, FLARE, MISCELLANEOUS, PUMP, GAS-DRIVEN-COMPRESSOR, TURBINE-GENERATOR, POWER-FROM-SHORE, OFFSHORE-WIND, LOADING, STORAGE, STEAM-TURBINE-GENERATOR, BOILER, HEATER ∣ dict[datetime, BASE-LOAD, COLD-VENTING-FUGITIVE, COMPRESSOR, FIXED-PRODUCTION-LOAD, FLARE, MISCELLANEOUS, PUMP, GAS-DRIVEN-COMPRESSOR, TURBINE-GENERATOR, POWER-FROM-SHORE, OFFSHORE-WIND, LOADING, STORAGE, STEAM-TURBINE-GENERATOR, BOILER, HEATER]</code>

- **ENERGY_USAGE_MODEL** *(required)*<span id="installations-fuelconsumers-energy_usage_model"></span><br/>  Definition of the energy usage model for the consumer.
  - **TYPE** *(required)*<span id="installations-fuelconsumers-energy_usage_model-type"></span><br/>    The type of the component
    - **DIRECT**<span id="installations-fuelconsumers-energy_usage_model-direct"></span><br/>      *Direct fuel consumption.*
      - **POWERLOSSFACTOR**<span id="installations-fuelconsumers-energy_usage_model-direct-powerlossfactor"></span><br/>        A factor that may be added to account for power line losses.<br/>        Allowed values: <code>text ∣ number ∣ integer</code>

      - **CONSUMPTION_RATE_TYPE**<span id="installations-fuelconsumers-energy_usage_model-direct-consumption_rate_type"></span><br/>        Defines the energy usage rate as stream day or calendar day. (<code>STREAM_DAY, CALENDAR_DAY</code>)

      - **FUEL_RATE** *(required)*<span id="installations-fuelconsumers-energy_usage_model-direct-fuel_rate"></span><br/>        Fixed power consumer with constant load.<br/>        Allowed values: <code>text ∣ number ∣ integer</code>


    - **COMPRESSOR**<span id="installations-fuelconsumers-energy_usage_model-compressor"></span><br/>      *Single compressor energy model.*
      - **POWERLOSSFACTOR**<span id="installations-fuelconsumers-energy_usage_model-compressor-powerlossfactor"></span><br/>        A factor that may be added to account for power line losses.<br/>        Allowed values: <code>text ∣ number ∣ integer</code>

      - **ENERGY_FUNCTION** *(required)*<span id="installations-fuelconsumers-energy_usage_model-compressor-energy_function"></span><br/>        The compressor energy function, reference to a compressor type facility model defined in FACILITY_INPUTS (<code>text</code>)

      - **RATE** *(required)*<span id="installations-fuelconsumers-energy_usage_model-compressor-rate"></span><br/>        Fluid (gas) rate through the compressor in Sm3/day<br/>        Allowed values: <code>text ∣ number ∣ integer</code>

      - **SUCTION_PRESSURE**<span id="installations-fuelconsumers-energy_usage_model-compressor-suction_pressure"></span><br/>        Fluid (gas) pressure at compressor inlet in bars<br/>        Allowed values: <code>text ∣ number ∣ integer</code>

      - **DISCHARGE_PRESSURE**<span id="installations-fuelconsumers-energy_usage_model-compressor-discharge_pressure"></span><br/>        Fluid (gas) pressure at compressor outlet in bars<br/>        Allowed values: <code>text ∣ number ∣ integer</code>


    - **COMPRESSOR_SYSTEM**<span id="installations-fuelconsumers-energy_usage_model-compressor_system"></span><br/>      *System of multiple compressors.*
      - **POWERLOSSFACTOR**<span id="installations-fuelconsumers-energy_usage_model-compressor_system-powerlossfactor"></span><br/>        A factor that may be added to account for power line losses.<br/>        Allowed values: <code>text ∣ number ∣ integer</code>

      - **COMPRESSORS** *(required)*<span id="installations-fuelconsumers-energy_usage_model-compressor_system-compressors"></span><br/>        The compressors in a compressor system.
        - **NAME** *(required)*<span id="installations-fuelconsumers-energy_usage_model-compressor_system-compressors-name"></span><br/>          Name of the compressor (<code>text</code>)

        - **COMPRESSOR_MODEL** *(required)*<span id="installations-fuelconsumers-energy_usage_model-compressor_system-compressors-compressor_model"></span><br/>          Reference to a compressor type facility model defined in FACILITY_INPUTS (<code>text</code>)


      - **TOTAL_SYSTEM_RATE**<span id="installations-fuelconsumers-energy_usage_model-compressor_system-total_system_rate"></span><br/>        Total fluid rate through the system<br/>        Allowed values: <code>text ∣ number ∣ integer</code>

      - **OPERATIONAL_SETTINGS** *(required)*<span id="installations-fuelconsumers-energy_usage_model-compressor_system-operational_settings"></span><br/>        Operational settings of the system.
        - **CROSSOVER**<span id="installations-fuelconsumers-energy_usage_model-compressor_system-operational_settings-crossover"></span><br/>          Set cross over rules in system operational setting. (<code>list[integer]</code>)

        - **RATES**<span id="installations-fuelconsumers-energy_usage_model-compressor_system-operational_settings-rates"></span><br/>          Set rate per consumer in a consumer system operational setting.<br/>          Allowed values: <code>list[text ∣ number ∣ integer]</code>

        - **RATE_FRACTIONS**<span id="installations-fuelconsumers-energy_usage_model-compressor_system-operational_settings-rate_fractions"></span><br/>          List of expressions defining fractional rate (of total system rate) per consumer.<br/>          Allowed values: <code>list[text ∣ number ∣ integer]</code>

        - **SUCTION_PRESSURES**<span id="installations-fuelconsumers-energy_usage_model-compressor_system-operational_settings-suction_pressures"></span><br/>          Set suction pressure per consumer in a consumer system operational setting.<br/>          Allowed values: <code>list[text ∣ number ∣ integer]</code>

        - **DISCHARGE_PRESSURES**<span id="installations-fuelconsumers-energy_usage_model-compressor_system-operational_settings-discharge_pressures"></span><br/>          Set discharge pressure per consumer in a consumer system operational setting.<br/>          Allowed values: <code>list[text ∣ number ∣ integer]</code>

        - **DISCHARGE_PRESSURE**<span id="installations-fuelconsumers-energy_usage_model-compressor_system-operational_settings-discharge_pressure"></span><br/>          Set discharge pressure equal for all consumers in a consumer system operational setting.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **SUCTION_PRESSURE**<span id="installations-fuelconsumers-energy_usage_model-compressor_system-operational_settings-suction_pressure"></span><br/>          Set suction pressure equal for all consumers in a consumer system operational setting.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>



    - **TABULATED**<span id="installations-fuelconsumers-energy_usage_model-tabulated"></span><br/>      *Tabulated energy function.*
      - **POWERLOSSFACTOR**<span id="installations-fuelconsumers-energy_usage_model-tabulated-powerlossfactor"></span><br/>        A factor that may be added to account for power line losses.<br/>        Allowed values: <code>text ∣ number ∣ integer</code>

      - **ENERGY_FUNCTION** *(required)*<span id="installations-fuelconsumers-energy_usage_model-tabulated-energy_function"></span><br/>        The tabulated energy function, reference to a tabular type facility model defined in FACILITY_INPUTS (<code>text</code>)

      - **VARIABLES** *(required)*<span id="installations-fuelconsumers-energy_usage_model-tabulated-variables"></span><br/>        Variables for the tabulated energy function
        - **NAME** *(required)*<span id="installations-fuelconsumers-energy_usage_model-tabulated-variables-name"></span><br/>          Name of variable. Must correspond exactly to header/column name in the energy function (<code>text</code>)

        - **EXPRESSION** *(required)*<span id="installations-fuelconsumers-energy_usage_model-tabulated-variables-expression"></span><br/>          Expression defining the variable<br/>          Allowed values: <code>text ∣ number ∣ integer</code>



    - **VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES**<span id="installations-fuelconsumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures"></span><br/>      *Variable-speed compressor train with multiple streams.*
      - **POWERLOSSFACTOR**<span id="installations-fuelconsumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-powerlossfactor"></span><br/>        A factor that may be added to account for power line losses.<br/>        Allowed values: <code>text ∣ number ∣ integer</code>

      - **RATE_UNIT**<span id="installations-fuelconsumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-rate_unit"></span><br/>        Defaults to SM3_PER_DAY, only SM3_PER_DAY implemented for now (<code>SM3_PER_DAY</code> · default: <code>SM3_PER_DAY</code>)

      - **COMPRESSOR_TRAIN_MODEL** *(required)*<span id="installations-fuelconsumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-compressor_train_model"></span><br/>        The compressor train model, reference to a compressor type model defined in MODELS (<code>text</code>)

      - **RATE_PER_STREAM** *(required)*<span id="installations-fuelconsumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-rate_per_stream"></span><br/>        Fluid (gas) rate for each of the streams going into or out of the compressor train (excluding the outlet of the last compressor stage) in Sm3/day<br/>        Allowed values: <code>list[text ∣ number ∣ integer]</code>

      - **SUCTION_PRESSURE** *(required)*<span id="installations-fuelconsumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-suction_pressure"></span><br/>        Fluid (gas) pressure at compressor train inlet in bars<br/>        Allowed values: <code>text ∣ number ∣ integer</code>

      - **DISCHARGE_PRESSURE** *(required)*<span id="installations-fuelconsumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-discharge_pressure"></span><br/>        Fluid (gas) pressure at compressor train outlet in bars<br/>        Allowed values: <code>text ∣ number ∣ integer</code>

      - **INTERSTAGE_CONTROL_PRESSURE**<span id="installations-fuelconsumers-energy_usage_model-variable_speed_compressor_train_multiple_streams_and_pressures-interstage_control_pressure"></span><br/>        Fluid (gas) pressure at an intermediate step in the compressor train<br/>        Allowed values: <code>text ∣ number ∣ integer</code>



  - **CONDITION**<span id="installations-fuelconsumers-energy_usage_model-condition"></span><br/>    Logical condition for the consumer to be used.<br/>    Allowed values: <code>text ∣ number ∣ integer</code>

  - **CONDITIONS**<span id="installations-fuelconsumers-energy_usage_model-conditions"></span><br/>    Logical conditions for the consumer to be used.<br/>    Allowed values: <code>list[text ∣ number ∣ integer]</code>


- **FUEL**<span id="installations-fuelconsumers-fuel"></span><br/>  The fuel used by the consumer.<br/>  Allowed values: <code>text ∣ dict[datetime, text]</code>

### VENTING_EMITTERS {#installations-venting_emitters}

Covers the direct emissions on the installation that are not consuming energy

- **TYPE** *(required)*<span id="installations-venting_emitters-type"></span><br/>  The type of the component
  - **OIL_VOLUME**<span id="installations-venting_emitters-oil_volume"></span><br/>    *Venting emitter based on oil loading/storage volumes with emission factors.*
    - **VOLUME** *(required)*<span id="installations-venting_emitters-oil_volume-volume"></span><br/>      The volume rate and emissions for the emitter of type OIL_VOLUME
      - **RATE** *(required)*<span id="installations-venting_emitters-oil_volume-volume-rate"></span><br/>        The oil loading/storage volume or volume/rate (<code>Rate</code>)
        - **CONDITION**<span id="installations-venting_emitters-oil_volume-volume-rate-condition"></span><br/>          A logical condition that determines whether the venting emitter oil volume rate is applicable. This condition must evaluate to true for the rate to be used.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **CONDITIONS**<span id="installations-venting_emitters-oil_volume-volume-rate-conditions"></span><br/>          A list of logical conditions that collectively determine whether the venting emitter oil volume rate is applicable. All conditions in the list must evaluate to true for the rate to be used.<br/>          Allowed values: <code>list[text ∣ number ∣ integer]</code>


      - **EMISSIONS** *(required)*<span id="installations-venting_emitters-oil_volume-volume-emissions"></span><br/>        The emission types and volume-emission-factors associated with oil loading/storage
        - **NAME** *(required)*<span id="installations-venting_emitters-oil_volume-volume-emissions-name"></span><br/>          Name of emission (<code>text</code>)

        - **EMISSION_FACTOR** *(required)*<span id="installations-venting_emitters-oil_volume-volume-emissions-emission_factor"></span><br/>          Loading/storage volume-emission factor<br/>          Allowed values: <code>text ∣ number ∣ integer</code>




  - **DIRECT_EMISSION**<span id="installations-venting_emitters-direct_emission"></span><br/>    *Venting emitter with direct emission rates (e.g. flaring, cold venting).*
    - **EMISSIONS** *(required)*<span id="installations-venting_emitters-direct_emission-emissions"></span><br/>      The emissions for the emitter of type DIRECT_EMISSION
      - **NAME** *(required)*<span id="installations-venting_emitters-direct_emission-emissions-name"></span><br/>        Name of emission (<code>text</code>)

      - **RATE** *(required)*<span id="installations-venting_emitters-direct_emission-emissions-rate"></span><br/>        The emission rate (<code>Rate</code>)
        - **CONDITION**<span id="installations-venting_emitters-direct_emission-emissions-rate-condition"></span><br/>          A logical condition that determines whether the venting emitter emission rate is applicable. This condition must evaluate to true for the rate to be used.<br/>          Allowed values: <code>text ∣ number ∣ integer</code>

        - **CONDITIONS**<span id="installations-venting_emitters-direct_emission-emissions-rate-conditions"></span><br/>          A list of logical conditions that collectively determine whether the venting emitter emission rate is applicable. All conditions in the list must evaluate to true for the rate to be used.<br/>          Allowed values: <code>list[text ∣ number ∣ integer]</code>





- **NAME** *(required)*<span id="installations-venting_emitters-name"></span><br/>  Name of venting emitter (<code>text</code>)

- **CATEGORY** *(required)*<span id="installations-venting_emitters-category"></span><br/>  Output category/tag. (<code>BASE-LOAD, COLD-VENTING-FUGITIVE, COMPRESSOR, FIXED-PRODUCTION-LOAD, FLARE, MISCELLANEOUS, PUMP, GAS-DRIVEN-COMPRESSOR, TURBINE-GENERATOR, POWER-FROM-SHORE, OFFSHORE-WIND, LOADING, STORAGE, STEAM-TURBINE-GENERATOR, BOILER, HEATER</code>)

---

## START {#start}

<code>datetime</code>

Global start date for eCalc calculations in &lt;YYYY-MM-DD&gt; format.

```yaml
START: YYYY-MM-DD
```

---

## END *(required)* {#end}

<code>datetime</code>

Global end date for eCalc calculations in &lt;YYYY-MM-DD&gt; format.

```yaml
END: YYYY-MM-DD
```

</div>