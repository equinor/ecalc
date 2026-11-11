---
title: Energy Components (Experimental)
sidebar_position: 0
description: Overview of the energy components, by category, with the energy types they accept and provide.
---

# Energy Components

All energy components in the `ENERGY_NETWORK`, grouped as sources, providers and consumers. On each page, the
connections on every component are coloured by energy type: inputs show what a component accepts, outputs show what it
provides. Two components can be connected when the output colour of one matches the input colour of the next.
Each component shows its inputs on the left: one connection means it accepts a single supplier, two connections of the same colour
mean it accepts two or more suppliers (junctions). Dashed connections of different colours are alternatives: the single
input can be any one of those energy types.
See the [Energy Reference](../energy-reference.mdx) for the full description of every element.

- [Sources](./sources.mdx): External energy entering the network. Sources only have an output.
- [Providers](./providers.mdx): Components that take energy in and provide energy to other components, such as converters and junctions.
- [Consumers](./consumers.mdx): Components that use energy from the network. Consumers only have an input.
