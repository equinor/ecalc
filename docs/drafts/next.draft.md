---
slug: "{{ version_slug }}"
title: "{{ version_title }}"
authors: ecalc-team
tags: [release, eCalc]
sidebar_position: -54
---

# eCalc {{ version }}

## Features

## Bug Fixes

- Import error when empty model item in YAML:

When YAML model had empty item, it is parsed as None and fail in replacing names.

```yaml
MODELS:
  - # <- empty item
  - NAME: ...
```

The replacing of names should work as intended, even with empty fields.

## Breaking changes

### CLI
