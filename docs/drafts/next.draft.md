---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -60
---

# eCalc {{ version }}

## Features

## Bug Fixes

## Breaking changes

- LTP/STP: Instead of defaulting to no data when the result is 0 (e.g. energy accumulation),
we will now explicitly set 0 in the result. This means that all the LTP and STP files generated
are consistent wrt. number of columns - always the same.

### CLI
