---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -42
---

# eCalc {{ version }}

## Features

## Bug Fixes

## Breaking changes

* Creation of time series resources now validates the correctness of the date/datetime.
  All dates within a file must follow either a dayfirst (dd.mm.yyyy hh:mm:ss) or ISO8601 format (yyyy.mm.dd hh:mm:ss).
  Mixing of datetime formats is not allowed.
  If any one line includes time, all lines must conform. I.e. it's either all or none lines with time.