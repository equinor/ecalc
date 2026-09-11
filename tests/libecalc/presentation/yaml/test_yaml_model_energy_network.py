"""End-to-end coverage of YamlModel.get_energy_network's expand_sampled_compressors hook:
a SAMPLED_COMPRESSOR written in YAML must reach the mapper already resolved into the
concrete unit types its FILE implies."""

from io import StringIO

import pytest

from libecalc.energy.energy_units import (
    ElectricalSource,
    FuelGasSource,
    GasTurbine,
    SampledCompressorElectricalConsumer,
    SampledCompressorFuelGasConsumer,
    SampledCompressorMechanicalConsumer,
)
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream

ENERGY_NETWORK_YAML = """
START: 2020-01-01
END: 2023-01-01

FUEL_TYPES:
  - NAME: fuel
    EMISSIONS:
      - NAME: co2
        FACTOR: 2.0

ENERGY_NETWORK:
  SOURCES:
{sources}
  UNITS:
    - NAME: compressor
      TYPE: SAMPLED_COMPRESSOR
      INPUT: {input_name}
      FILE: compressor.csv
      RATE: 50000

INSTALLATIONS:
  - NAME: installation
    HCEXPORT: 0
    FUELCONSUMERS:
      - NAME: flare
        CATEGORY: FLARE
        FUEL: fuel
        ENERGY_USAGE_MODEL:
          TYPE: DIRECT
          FUELRATE: 50
"""


def _yaml_model(yaml_model_factory, sources: str, input_name: str, headers: list[str], rows: list[list[float]]):
    configuration = ResourceStream(
        name="energy_network_model",
        stream=StringIO(ENERGY_NETWORK_YAML.format(sources=sources, input_name=input_name)),
    )
    resource = MemoryResource(headers=headers, data=[list(column) for column in zip(*rows)])
    return yaml_model_factory(configuration=configuration, resources={"compressor.csv": resource})


@pytest.mark.parametrize(
    ("sources", "input_name", "headers", "rows", "expected_types", "expected_names"),
    [
        (
            "    - NAME: fuel_gas\n      TYPE: FUEL_GAS_SOURCE",
            "fuel_gas",
            ["RATE", "FUEL"],
            [[1000, 100], [2000, 150]],
            [FuelGasSource, SampledCompressorFuelGasConsumer],
            ["fuel_gas", "compressor"],
        ),
        (
            "    - NAME: grid\n      TYPE: ELECTRICAL_SOURCE",
            "grid",
            ["RATE", "POWER"],
            [[1000, 1.0], [2000, 1.5]],
            [ElectricalSource, SampledCompressorElectricalConsumer],
            ["grid", "compressor"],
        ),
        (
            "    - NAME: fuel_gas\n      TYPE: FUEL_GAS_SOURCE",
            "fuel_gas",
            ["RATE", "FUEL", "POWER"],
            [[1000, 100, 1.0], [2000, 150, 1.5]],
            [FuelGasSource, GasTurbine, SampledCompressorMechanicalConsumer],
            ["fuel_gas", "compressor-turbine", "compressor"],
        ),
    ],
)
def test_get_energy_network_expands_sampled_compressors(
    yaml_model_factory, sources, input_name, headers, rows, expected_types, expected_names
):
    model = _yaml_model(yaml_model_factory, sources, input_name, headers, rows)

    network, energy_units, consumer_expressions = model.get_energy_network()

    assert network is not None
    assert [type(energy_unit) for energy_unit in energy_units] == expected_types
    assert [energy_unit.get_name() for energy_unit in energy_units] == expected_names
    assert {energy_unit.get_id() for energy_unit in energy_units} == set(network.get_nodes())
    assert len(network.get_connections()) == len(energy_units) - 1
    # Deriving energy usage from FILE is not yet implemented, so a sampled unit's RATE
    # never becomes a consumer expression.
    assert consumer_expressions == {}


def test_get_energy_network_rejects_input_energy_type_mismatching_file(yaml_model_factory):
    model = _yaml_model(
        yaml_model_factory,
        sources="    - NAME: grid\n      TYPE: ELECTRICAL_SOURCE",
        input_name="grid",
        headers=["RATE", "FUEL"],
        rows=[[1000, 100], [2000, 150]],
    )

    with pytest.raises(ValueError, match="'compressor': INPUT provides ELECTRICAL, but FILE has a FUEL column"):
        model.get_energy_network()
