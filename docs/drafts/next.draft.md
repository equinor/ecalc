---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -59
---

# eCalc {{ version }}

## Features

## Bug Fixes

## Breaking changes

### Facility Inputs Adjustments

`ADJUSTMENT` section for `FACILITY_INPUTS` has been removed. This section was rarely used and was of limited usefulness. The original data was adjusted early in the process, 
and users would not get any extra functionality from using this section, rather than being able to reuse the same original data with different adjustments, or to make it easy to adjust
data on-the-fly, to e.g. reflect deterioration over time. See migration guide for how to adjust data now.

### CLI

- `--csv` will no longer disable the csv file, `--no-csv` should be used instead.
