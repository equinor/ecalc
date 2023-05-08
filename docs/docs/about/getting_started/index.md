---
title: Getting started
sidebar_position: 2
description: Getting started with eCalc
---

# API Reference

:::info
Currently the *only* officially supported method is the [eCalc CLI](cli/index.md).
:::

There are three options to run eCalc models:

- [eCalc CLI](cli/index.md)
- [eCalc Python library](library/index.md)

## What method should I choose?

### eCalc CLI
Choose the [eCalc CLI](cli/index.md) option if you:

- want to integrate your model(s) in an [FMU](https://wiki.equinor.com/wiki/index.php/FMU_portal_home) setup, dependent on ERT, WebViz etc.
- prefer working in your own text editor in a Unix environment
- want full control over your eCalc environment [this will change]
- want to have access to old versions of eCalc

:::note
The eCalc CLI option is available from your local machine, or an RGS node. See [CLI](cli/index.md) for getting started.
:::

### Python Library
Choose the [Python Library](library/index.md) option if you:

- Are a developer or advanced user, and want to build eCalc models and get results programmatically
- Use Python, and you need to use (parts of) eCalc as a dependency
- Need access to "inner core functionality" of eCalc

:::note
Python Library is not yet available
:::