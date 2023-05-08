---
sidebar_label: "CLI"
---

# `ecalc`

**Usage**:

```console
$ ecalc [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--log [CRITICAL|FATAL|ERROR|WARNING|INFO|DEBUG|NOTSET]`: Set the loglevel.  [default: INFO]
* `--log-folder PATH`: Store log files in a folder
* `--version`: Show current eCalc™ version.
* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `run`
* `selftest`: Test that eCalc has been successfully...
* `show`: Command to show information in the model...

## `ecalc run`

**Usage**:

```console
$ ecalc run [OPTIONS] MODEL_FILE
```

**Arguments**:

* `MODEL_FILE`: The Model YAML-file specifying time series inputs, facility inputs and the relationship between energy consumers.  [required]

**Options**:

* `-f, --output-frequency, --outputfrequency [NONE|YEAR|MONTH|DAY]`: Frequency of output. Options are DAY, MONTH, YEAR. If not specified, it will give time steps equal to the union of all input given with INFLUENCE_TIME_VECTOR set to True. Down-sampling the result may lead to loss of data, and rates such as MW may not add up to cumulative values  [default: NONE]
* `-c, --csv`: Toggle output of csv data.  [default: True]
* `--json`: Toggle output of json output.
* `-o, --output-folder, --outputfolder PATH`: Outputfolder. Defaults to output/ relative to the yml setup file
* `-n, --name-prefix, --nameprefix TEXT`: Name prefix for output data. Defaults to name of setup file.
* `--ltp-export`: In addition to standard output, a specific Long Term Prognosis (LTP) file will be provided for simple export of LTP relevant data (Tabular Separated Values).
* `--stp-export`: In addition to standard output, a specific Short Term Prognosis (STP) file will be provided for simple export of STP relevant data (Tabular Separated Values).
* `--flow-diagram`: Output the input model formatted to be displayed in a custom flow diagram format in JSON
* `--detailed-output, --detailedoutput`: Output detailed output. When False you will get basic results such as energy usage, power, time vector.
* `--date-format-option [0|1|2]`: Date format option. 0: "YYYY-MM-DD HH:MM:SS" (Accepted variant of ISO8601), 1: "YYYYMMDD HH:MM:SS" (ISO8601), 2: "DD.MM.YYYY HH:MM:SS". Default 0 (ISO 8601)  [default: 0]
* `--help`: Show this message and exit.

## `ecalc selftest`

Test that eCalc has been successfully installed

**Usage**:

```console
$ ecalc selftest [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `ecalc show`

Command to show information in the model or results.

**Usage**:

```console
$ ecalc show [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `results`: Show results.
* `yaml`: Show yaml model.

### `ecalc show results`

Show results. You need to run eCalc™ before this will be available.

**Usage**:

```console
$ ecalc show results [OPTIONS]
```

**Options**:

* `-n, --name TEXT`: Filter the results to only show the component with this name
* `--output-format [csv|json]`: Show the data in this format.  [default: json]
* `--file PATH`: Write the data to a file with the specified name.
* `--output-folder PATH`: Output folder. Defaults to current working directory
* `--detailed-output`: Output detailed output. When False you will get basic energy usage and emissions results
* `--date-format-option [0|1|2]`: Date format option. 0: "YYYY-MM-DD HH:MM:SS" (Accepted variant of ISO8601), 1: "YYYYMMDD HH:MM:SS" (ISO8601), 2: "DD.MM.YYYY HH:MM:SS". Default 0 (ISO 8601)  [default: 0]
* `-f, --output-frequency [NONE|YEAR|MONTH|DAY]`: Frequency of output. Options are DAY, MONTH, YEAR. If not specified, it will give time steps equal to the union of all input given with INFLUENCE_TIME_VECTOR set to True. Down-sampling the result may lead to loss of data, and rates such as MW may not add up to cumulative values  [default: NONE]
* `--help`: Show this message and exit.

### `ecalc show yaml`

Show yaml model. This will show the yaml after processing !include.

**Usage**:

```console
$ ecalc show yaml [OPTIONS] MODEL_FILE
```

**Arguments**:

* `MODEL_FILE`: YAML file specifying time series inputs, facility inputs and the relationship between energy consumers.  [required]

**Options**:

* `--file PATH`: Write the data to a file with the specified name.
* `--help`: Show this message and exit.

