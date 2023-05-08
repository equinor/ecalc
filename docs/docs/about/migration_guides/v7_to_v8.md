---
title: v7 to v8
description: v7 to v8 migration
sidebar_position: 2
---

# v7 to v8

In this migration guide you will find:

1. [YAML changes](#yaml-migration)
2. [CLI changes](#cli-migration)

## Yaml migration

### Migration overview

This doc guides you through migrating an existing eCalc™ model from version v7 to v8.

We try to make this as easy as possible, and provide a step-by-step migration guide.

### Main differences
1. All component names must be unique to avoid ambiguity in reporting
2. UNITS are required when setting up compressor and pump charts
3. Restrict allowed characters in component names and emission names
4. NAME no longer used for LTP reporting, use CATEGORY instead
5. Not possible to use custom category names, pre-defined categories must be uppercase with hyphen as separator (i.e. FUEL-GAS)

#### 1. All component names must be unique

All component names must be unique in order to avoid ambiguity in reporting. Components include asset/ecalc-model, installation,
generator sets, electricity consumers, fuel consumers and direct emitters.

```yaml title="main.yaml"
INSTALLATIONS:
  # This is old
  - NAME: Installation
    ...
    
    GENERATORSETS:
      # This is old
      - NAME: Genset
        ...
        CONSUMERS:
          # This is old
          - NAME: Consumer
            ...
          # This is old
          - NAME: Consumer
            ...
      # This is old
      - NAME: Genset
        ...
            
    FUELCONSUMERS:
      # This is old
      - NAME: FuelConsumer
        ...
      # This is old
      - NAME: FuelConsumer
        ...
    
    DIRECT_EMITTER:
      # This is old
      - NAME: DirectEmitter
        ...
      # This is old
      - NAME: DirectEmitter
        ...
    # This is old
  - NAME: Installation
    ...
```

This model is no longer valid, and the duplicated installation names are highlighted.
To make this model valid these names needs to be changed. For example:

```yaml title="main.yaml"
INSTALLATIONS:
  # This is new
  - NAME: Installation_A
    ...
    
    GENERATORSETS:
      # This is new
      - NAME: Genset_A
        ...
        CONSUMERS:
          # This is new
          - NAME: Consumer_A
            ...
          # This is new
          - NAME: Consumer_B
            ...
      # This is new
      - NAME: Genset_B
        ...
            
    FUELCONSUMERS:
      # This is new
      - NAME: FuelConsumer_A
        ...
      # This is new
      - NAME: FuelConsumer_B
        ...
    
    DIRECT_EMITTER:
      # This is new
      - NAME: DirectEmitter_A
        ...
      # This is new
      - NAME: DirectEmitter_B
        ...
  # This is new
  - NAME: Installation_B
    ...
```

This will make it possible to attribute results to each consumer by name, and removes any an ambiguity
when interpreting eCalc™ results.

See [INSTALLATION](../references/keywords/INSTALLATIONS.md),
[GENERATORSET](../references/keywords/GENERATORSETS.md),
[CONSUMERS](../references/keywords/CONSUMERS.md),
[FUELCONSUMERS](../references/keywords/FUELCONSUMERS.md),
[DIRECT_EMITTER](../references/keywords/DIRECT_EMITTERS.md)
for more details about the relevant keywords.

:::tip Are you using power from shore?
We have implemented temporal categories for consumers to support the power from shore implementation in use. 

Instead of duplicating the generator set and setting the `POWER-FROM-SHORE` category, 
it is now possible to change the category at a certain date. This is the same syntax as other temporal models.

```yaml
CATEGORY:
  2020-01-01: TURBINE-GENERATOR
  2030-01-01: POWER-FROM-SHORE
```

See [Power from shore](../modelling/setup/facility_inputs/generator_modelling.md#power-from-shore) for more information.
:::

#### 2. UNITS for pump and compressor charts

Compressor and pump charts has previously had implicit units, without requiring the operator to specify what
units are actually being used. This increases the risk of wrong specification, and makes it more difficult to hand
over models.

To amend this issue, and to open up for more flexibility in regard to units, it is now mandatory to specify.

To keep the old defaults you can do the following:

```yaml title="main.yaml"
FACILITY_INPUTS:
  - NAME: single_speed_pump_chart
    FILE: <some input csv>
    # highlight-next-line
    TYPE: PUMP_CHART_SINGLE_SPEED
    # highlight-new-start
    UNITS:
      RATE: AM3_PER_HOUR
      HEAD: M
      EFFICIENCY: PERCENTAGE
    # highlight-new-end
  - NAME: variable_speed_pump_chart
    FILE: <some input csv>
    # highlight-next-line
    TYPE: PUMP_CHART_VARIABLE_SPEED
    # highlight-new-start
    UNITS:
      RATE: AM3_PER_HOUR
      HEAD: M
      EFFICIENCY: PERCENTAGE
    # highlight-new-end

MODELS:
  - NAME: single_speed_compressor_chart
    # highlight-start
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: SINGLE_SPEED
    # highlight-end
    # highlight-new-start
    UNITS:
      HEAD: M
      RATE: AM3_PER_HOUR
      EFFICIENCY: FRACTION
    # highlight-new-end
    CURVES:
      ...
  - NAME: variable_speed_compressor_chart
    # highlight-start
    TYPE: COMPRESSOR_CHART
    CHART_TYPE: VARIABLE_SPEED
    # highlight-end
    # highlight-new-start
    UNITS:
      HEAD: M
      RATE: AM3_PER_HOUR
      EFFICIENCY: FRACTION
    # highlight-new-end
    CURVES:
      ...

...
```

See [COMPRESSOR CHART](../modelling/setup/models/compressor_modelling/compressor_charts/index.md)
and [PUMP CHART](../modelling/setup/facility_inputs/pump_modelling/pump_charts)
for more details about the relevant keywords.


#### 3. Restrict allowed characters in component names and emission names

Component names can now only consist of letters (a-z, upper and lower case), numbers (0-9), underscore (`_`), hyphen (`-`) and space (` `).

Emission names can now only consist of letters (a-z, upper and lower case), numbers (0-9) and underscore (`_`).


#### 4. NAME no longer used for LTP reporting, use CATEGORY instead

We have categories for FLARE and COLD-VENTING-FUGITIVE, and have introduced categories for LOADING and STORAGE. These should now be used instead of NAME.

```yaml title="main.yaml"
INSTALLATIONS:
  - NAME: Installation_A
    ...
    
    GENERATORSETS:
      - NAME: Genset_A
        ...
        CONSUMERS:
          - NAME: Consumer_A
            ...
            
    FUELCONSUMERS:
      # This is old
      - NAME: loading # Name will no longer be used in LTP reporting
        # This is new
        CATEGORY: LOADING # Category must be used to include it in LTP reporting
        FUEL: Fuel_A
        ENERGY_USAGE_MODEL:
          TYPE: DIRECT
          FUELRATE: Oil_rate_per_timestep
          ...
      # This is old
      - NAME: storage # Name will no longer be used in LTP reporting
        # This is new
        CATEGORY: STORAGE # Category must be used to include it in LTP reporting
        FUEL: Fuel_B
        ENERGY_USAGE_MODEL:
          TYPE: DIRECT
          FUELRATE: Oil_rate_per_timestep
          ...      
      # This is old
      - NAME: flare # Name will no longer be used in LTP reporting
        # This is new
        CATEGORY: FLARE # Category must be used to include it in LTP reporting
        FUEL: Fuel_C
        ENERGY_USAGE_MODEL:
          TYPE: DIRECT
          FUELRATE: Oil_rate_per_timestep
          ...
      # This is old
      - NAME: cold_venting_fugitives_nmvoc # Name will no longer be used in LTP reporting
        # This is new
        CATEGORY: COLD-VENTING-FUGITIVE # Category must be used to include it in LTP reporting
        FUEL: Fuel_D  # The fuel specification determines what emissions will be used in LTP
        ENERGY_USAGE_MODEL:
          TYPE: DIRECT
          FUELRATE: Oil_rate_per_timestep
          ...      
 
...
```


#### 5. Not possible to use custom category names, pre-defined categories must be uppercase with hyphen as separator (i.e. FUEL-GAS)

Only a limited pre-defined set of categories is valid input to the CATEGORY-keyword, it is no longer possible to use custom names. 
The input is case-sensitive and must match exactly with the pre-defined names. See [CLI Docs](../references/keywords/CATEGORY) for full documentation.

## CLI migration

This version includes some changes to how the CLI is invoked and changes to default behavior.

1. Invoking eCalc™ directly is no longer supported, use `ecalc run` instead.
2. Log level should be specified as the first argument + log to file
3. Model yaml-file needs to come last
4. Extrapolation (correction) is now always used and cannot be disabled
5. Argument for LTP export has changed from: `--centuries-ltp-export` to `--ltp-export`
6. Simple results are now default for json

#### 1. Invoking eCalc™ directly is no longer supported, use `ecalc run` instead.

To make it possible to add `ecalc show` we added the `ecalc run` command. In v8 it is required to specify `run` when calculating a model.

If you previously ran eCalc™ with this command

~~~~~~~~bash
$ ecalc ./my-model.yaml
~~~~~~~~

you should now use 

~~~~~~~~bash
$ ecalc run ./my-model.yaml
~~~~~~~~

#### 2. Log level should be specified as the first argument + log to file

Previously you could specify the `--log` argument after `run`, this is no longer possible.

This is the new way of specifying log level.

~~~~~~~~bash
$ ecalc --log DEBUG run ./my-model.yaml
~~~~~~~~

In addition we are introducing `--log-folder <path>` where you can direct and store the log in a given path to easily
look at the log of running later than scrolling in the terminal window. Due to the excessive amount of logs that eCalc
produces when running at low log levels, we have set the log to only log at WARNING and above (WARNING + ERROR messages).
The user must make sure that the path/folder exists before running and that you have correct permissions, as eCalc will NOT
do that for you.

~~~~~~~~bash
$ ecalc --log DEBUG --log-folder . run ./my-model.yaml
~~~~~~~~

As you see above, the argument **MUST** be added **BEFORE** the `run` argument.

#### 3. Model yaml-file needs to come last

When running eCalc™ you will now need to set the model file argument last.

`ecalc [OPTIONS] COMMAND [ARGS] [MODEL YAML-file]`

See the [CLI Docs](../references/cli_reference) or run `ecalc --help` for the full documentation.

#### 4. Extrapolation correction is no longer optional

We have removed the extrapolation correction argument. eCalc™ will now always "extrapolate" values.
The main reason for making this change was that the feature was in general always used, in addition to being a confusing term. 
Let us know if you have a use-case where this was needed.

#### 5. Argument for LTP export has changed from: `--centuries-ltp-export` to `--ltp-export`

To prepare for Open Source and to make the LTP export more agnostic (even though the column names are heavily 
affected by Centuries), we simplify the argument to get LTP results. See [CLI Docs](../references/cli_reference) for 
full documentation.

#### 6. Simple results are now default for json
Detailed output (or any json) should mainly be used for QA and advanced users, and is no longer shown by default. To keep old behavior, the user now
needs to use the --detailed-output option when running the CLI. See [CLI reference docs](../references/cli_reference#ecalc-run)
for more details.