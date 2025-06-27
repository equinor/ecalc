    ---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -50
---

# eCalc {{ version }}

## Features

## Bug Fixes

## Breaking changes

- The END keyword is now required in the YAML file. The dates in each row in the different time series resource input files corresponds to the start date of a period in the eCalc simulation. To avoid having to guess when the last period in the eCalc model should end it is now required to explicitly specify the end date using the END keyword.  