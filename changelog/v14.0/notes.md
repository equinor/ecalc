## Added

- Added the `ENERGY_NETWORK` YAML types (sources, consumers, converters, junctions and cables), with a reference and examples.
- `ENERGY_NETWORK` models are evaluated, so energy demand and flow are solved from the YAML.

## Changed

- `PUMP_PROCESS_SIMULATIONS`: pump head is bounded by the maximum head of the pump chart, not only the minimum. Power and pressure no longer grow without limit outside the chart.
