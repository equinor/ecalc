---
title: Energy Units (Experimental)
sidebar_position: 0
description: Overview of the energy units, by category, with the energy types they accept and provide.
---

# Energy Units

All energy units in the `ENERGY_NETWORK`, grouped as sources, converters, transporters, junctions and consumers. On each page, the
connections on every unit are coloured by energy type: inputs show what a unit accepts, outputs show what it
provides. Two units can be connected when the output colour of one matches the input colour of the next.
Each unit shows its inputs on the left: one connection means it accepts a single supplier, two connections of the same
colour mean it accepts two or more suppliers (junctions). Dashed connections of different colours are alternatives: the
single input can be any one of those energy types.
See the [Energy Reference](../energy-reference.mdx) for the full description of every element.

- [Sources](./sources.mdx): External energy entering the network. Sources only have an output.
- [Converters](./converters.mdx): Convert one energy type into another. Each converter has one input.
- [Transporters](./transporters.mdx): Carry energy from one place to another, with losses. The energy type is the same on both sides.
- [Junctions](./junctions.mdx): Collect several suppliers of the same energy type and dispatch demand between them.
- [Consumers](./consumers.mdx): Use energy from the network. Consumers only have an input.
