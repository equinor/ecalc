# Process Domain Entities

This directory contains the core **entity** definitions for the Process Domain.

Entities represent objects with a distinct identity that persists over time and through state changes. In the context of the process domain, these primarily include:

*   **`base.py`**: Defines the abstract `ProcessUnit` base class, which all specific process equipment entities inherit from.
*   **`process_units/`**: Contains individual modules/directories for each specific type of process equipment (e.g., `compressor/`, `cooler/`, `pump/`).
    *   Each process unit entity defined here is responsible for its specific processing logic.
    *   They typically operate on one or more input `Stream` objects and produce one or more output `Stream` objects.
*   **`shaft/`**: Contains the `Shaft` entity, representing a physical shaft with properties like speed, potentially shared by multiple compressor stages.

## Purpose

The entities defined here encapsulate the state and behavior of individual components within a process flowsheet. They are central to building and solving the `ProcessGraph`.

## Migration Note

Legacy process unit definitions from the previous codebase structure will be gradually ported to new, dedicated entity classes within this directory structure. The aim is to create clear, well-defined, and testable domain objects.