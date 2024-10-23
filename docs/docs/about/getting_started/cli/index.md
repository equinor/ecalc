---
title: CLI
sidebar_position: 2
description: Getting started with eCalc CLI
---
# eCalc CLI

:::info
It is currently **recommended** to use the CLI instead of the Python library directly due to upcoming breaking changes in the Python library
:::

The current recommended way to use eCalc is through the CLI (Command Line Interpreter). This is a part of the
eCalc Python library, and should be accessible from the command line as `ecalc`.

You must minimum have **Python 3.11** installed to use eCalc.

See all commands and options in the [CLI reference](/about/getting_started/cli/cli_reference.md)

## Example Usage

#### Use show command to inspect results

First run ecalc (here shown with default output folder)

~~~~~~~~bash
$ ecalc run /somelocation/myfield.yaml --output-folder output
~~~~~~~~

Enter the output folder

~~~~~~~~bash
$ cd output
~~~~~~~~

Show results for a single component

~~~~~~~~bash
$ ecalc show results --name waterinj --output-format json
~~~~~~~~

or as csv

~~~~~~~~bash
$ ecalc show results --name waterinj --output-format csv
~~~~~~~~

or write the full csv result to a file (this will give the same output as `ecalc run` with the csv option)

~~~~~~~~bash
$ ecalc show results --output-format csv --file results.csv
~~~~~~~~

#### Output Monthly CSV data
~~~~~~~~bash
$ ecalc run -f MONTH /somelocation/myfield.yml
~~~~~~~~

#### Specify different output folder
~~~~~~~~bash
$ ecalc run -o /somedirectory/foo/bar/ /somelocation/myfield.yml
~~~~~~~~

#### Specify a different naming prefix to outputs
~~~~~~~~bash
$ ecalc run -n myfield_myproject /somelocation/myfield.yml
~~~~~~~~

#### Show stack trace for debugging
~~~~~~~~bash
$ ecalc run --log DEBUG /somelocation/myfield.yml
~~~~~~~~
