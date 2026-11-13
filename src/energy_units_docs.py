from energy_mermaid import (
    CATEGORIES,
    CATEGORY_CONSUMERS,
    CATEGORY_CONVERTERS,
    CATEGORY_JUNCTIONS,
    CATEGORY_SOURCES,
    CATEGORY_TRANSPORTERS,
    generate_energy_units_mermaid,
)

ENERGY_UNITS_DIRECTORY_NAME = "energy-units"

ENERGY_UNIT_CATEGORY_DETAILS: dict[str, tuple[str, str, list[str]]] = {
    CATEGORY_SOURCES: (
        "sources",
        "External energy entering the network. Sources only have an output.",
        [],
    ),
    CATEGORY_CONVERTERS: (
        "converters",
        "Convert one energy type into another. Each converter has one input.",
        ["`GENERATOR` accepts fuel gas or diesel and provides electrical power."],
    ),
    CATEGORY_TRANSPORTERS: (
        "transporters",
        "Carry energy from one place to another, with losses. The energy type is the same on both sides.",
        [],
    ),
    CATEGORY_JUNCTIONS: (
        "junctions",
        "Collect several suppliers of the same energy type and dispatch demand between them.",
        [],
    ),
    CATEGORY_CONSUMERS: (
        "consumers",
        "Use energy from the network. Consumers only have an input.",
        [
            "`COMPRESSOR_SAMPLED` accepts mechanical energy and refers to a compressor. Its `FILE` has a "
            "`SHAFT_POWER` column.",
            "`DRIVE_TRAIN` accepts mechanical energy and refers to a shaft.",
        ],
    ),
}


def generate_energy_units_index_markdown() -> str:
    links = "\n".join(
        f"- [{category}](./{ENERGY_UNIT_CATEGORY_DETAILS[category][0]}.mdx): {ENERGY_UNIT_CATEGORY_DETAILS[category][1]}"
        for category in CATEGORIES
    )
    category_names = ", ".join(category.lower() for category in CATEGORIES[:-1]) + f" and {CATEGORIES[-1].lower()}"
    return f"""\
---
title: Energy Units (Experimental)
sidebar_position: 0
description: Overview of the energy units, by category, with the energy types they accept and provide.
---

# Energy Units

All energy units in the `ENERGY_NETWORK`, grouped as {category_names}. On each page, the
connections on every unit are coloured by energy type: inputs show what a unit accepts, outputs show what it
provides. Two units can be connected when the output colour of one matches the input colour of the next.
Each unit shows its inputs on the left: one connection means it accepts a single supplier, two connections of the same
colour mean it accepts two or more suppliers (junctions). Dashed connections of different colours are alternatives: the
single input can be any one of those energy types.
See the [Energy Reference](../energy-reference.mdx) for the full description of every element.

{links}
"""


def generate_energy_units_category_markdown(category: str, sidebar_position: int) -> str:
    _, description, notes = ENERGY_UNIT_CATEGORY_DETAILS[category]
    notes_section = "\n" + "".join(f"- {note}\n" for note in notes) if notes else ""
    return f"""\
---
title: {category} (Experimental)
sidebar_position: {sidebar_position}
description: {description}
---

# {category}

{description} Connections are coloured by the energy type they accept or provide.

```mermaid
{generate_energy_units_mermaid(category)}
```
{notes_section}"""


def generate_energy_units_pages() -> dict[str, str]:
    pages = {"index.md": generate_energy_units_index_markdown()}
    for position, category in enumerate(CATEGORIES, start=1):
        file_stem = ENERGY_UNIT_CATEGORY_DETAILS[category][0]
        pages[f"{file_stem}.mdx"] = generate_energy_units_category_markdown(category, position)
    return pages
