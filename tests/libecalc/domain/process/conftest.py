from typing import Final

import pytest

from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.entities.process_units.temperature_setter import TemperatureSetter
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.process_solver.search_strategies import (
    CONVERGENCE_TOLERANCE,
    BinarySearchStrategy,
    ScipyRootFindingStrategy,
)
from libecalc.domain.process.process_solver.stream_constraint import PressureStreamConstraint
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.fluid_stream import FluidService
from libecalc.domain.process.value_objects.fluid_stream.fluid import Fluid
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_properties import FluidProperties
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream


@pytest.fixture
def medium_composition() -> FluidComposition:
    """Create a medium gas composition (19.4 kg/kmol) for testing.
    This matches the predefined MEDIUM_MW_19P4 composition."""
    return FluidComposition(
        nitrogen=0.74373,
        CO2=2.415619,
        methane=85.60145,
        ethane=6.707826,
        propane=2.611471,
        i_butane=0.45077,
        n_butane=0.691702,
        i_pentane=0.210714,
        n_pentane=0.197937,
        n_hexane=0.368786,
    )


@pytest.fixture
def ultra_rich_composition() -> FluidComposition:
    """Create an ultra rich gas composition (24.6 kg/kmol) for testing.
    This matches the predefined ULTRA_RICH_MW_24P6 composition."""
    return FluidComposition(
        nitrogen=3.433045573,
        CO2=0.341296928,
        methane=62.50752861,
        ethane=15.64946798,
        propane=13.2202369,
        i_butane=1.606103192,
        n_butane=2.479421803,
        i_pentane=0.351335073,
        n_pentane=0.291106204,
        n_hexane=0.120457739,
    )


def create_mock_fluid_properties(
    pressure_bara: float,
    temperature_kelvin: float,
    density: float = 50.0,
    enthalpy_joule_per_kg: float = 10000.0,
    z: float = 0.8,
    kappa: float = 1.3,
    vapor_fraction_molar: float = 1.0,
    molar_mass: float = 0.018,
    standard_density: float = 0.8,
) -> FluidProperties:
    """Create mock FluidProperties for unit testing without JVM (NeqSim).

    Note: composition and eos_model are no longer part of FluidProperties.
    Use create_mock_fluid_model for those.
    """
    return FluidProperties(
        temperature_kelvin=temperature_kelvin,
        pressure_bara=pressure_bara,
        density=density,
        enthalpy_joule_per_kg=enthalpy_joule_per_kg,
        z=z,
        kappa=kappa,
        vapor_fraction_molar=vapor_fraction_molar,
        molar_mass=molar_mass,
        standard_density=standard_density,
    )


def create_mock_fluid_model(
    composition: FluidComposition,
    eos_model: EoSModel = EoSModel.SRK,
) -> FluidModel:
    """Create mock FluidModel for unit testing."""
    return FluidModel(composition=composition, eos_model=eos_model)


@pytest.fixture
def mock_fluid_model(medium_composition) -> FluidModel:
    """Create mock fluid model for testing."""
    return create_mock_fluid_model(composition=medium_composition, eos_model=EoSModel.SRK)


@pytest.fixture
def mock_fluid_properties() -> FluidProperties:
    """Create mock fluid properties for testing."""
    return create_mock_fluid_properties(
        pressure_bara=20.0,
        temperature_kelvin=310.0,
    )


@pytest.fixture
def mock_fluid_properties_factory():
    """Factory to create mock fluid properties with custom P and T."""

    def factory(
        pressure_bara: float,
        temperature_kelvin: float,
        enthalpy_joule_per_kg: float = 10000.0,
    ) -> FluidProperties:
        return create_mock_fluid_properties(
            pressure_bara=pressure_bara,
            temperature_kelvin=temperature_kelvin,
            enthalpy_joule_per_kg=enthalpy_joule_per_kg,
        )

    return factory


@pytest.fixture
def mock_fluid(mock_fluid_model, mock_fluid_properties) -> Fluid:
    """Create a mocked Fluid for testing."""
    return Fluid(fluid_model=mock_fluid_model, properties=mock_fluid_properties)


@pytest.fixture
def fluid_stream_mock(mock_fluid) -> FluidStream:
    """Create a mocked fluid stream for testing."""
    return FluidStream(fluid=mock_fluid, mass_rate_kg_per_h=100.0)


class SimpleProcessUnit(ProcessUnit):
    def __init__(
        self,
        pressure_multiplier: float,
        fluid_service: FluidService,
        process_unit_id: ProcessUnitId | None = None,
    ):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnit._create_id()
        self._pressure_multiplier = pressure_multiplier
        self._fluid_service = fluid_service

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            pressure_bara=inlet_stream.pressure_bara * self._pressure_multiplier,
            standard_rate_m3_per_day=inlet_stream.standard_rate_sm3_per_day,
            temperature_kelvin=inlet_stream.temperature_kelvin,
        )


@pytest.fixture
def simple_process_unit_factory(fluid_service):
    def create_simple_process_unit(pressure_multiplier: float = 1):
        return SimpleProcessUnit(
            pressure_multiplier=pressure_multiplier,
            fluid_service=fluid_service,
        )

    return create_simple_process_unit


@pytest.fixture
def compressor_factory(fluid_service):
    def create_compressor(chart_data: ChartData):
        return Compressor(
            compressor_chart=chart_data,
            fluid_service=fluid_service,
        )

    return create_compressor


@pytest.fixture
def stage_units_factory(fluid_service):
    def create_stage_units(
        compressor: Compressor,
        shaft: Shaft,
        temperature_kelvin: float = 303.15,
        pressure_drop_ahead_of_stage: float = 0.0,
        remove_liquid_after_cooling: bool = False,
    ) -> list[ProcessUnit]:
        assert isinstance(compressor, Compressor)
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        fluid_service = NeqSimFluidService.instance()
        units: list[ProcessUnit] = []

        if pressure_drop_ahead_of_stage:
            from libecalc.domain.process.entities.process_units.choke import Choke

            units.append(
                Choke(
                    fluid_service=fluid_service,
                    pressure_change=pressure_drop_ahead_of_stage,
                )
            )

        units.append(
            TemperatureSetter(
                required_temperature_kelvin=temperature_kelvin,
                fluid_service=fluid_service,
            )
        )

        if remove_liquid_after_cooling:
            from libecalc.domain.process.entities.process_units.liquid_remover import LiquidRemover

            units.append(
                LiquidRemover(
                    fluid_service=fluid_service,
                )
            )

        shaft.connect(compressor)
        units.append(compressor)

        return units

    return create_stage_units


@pytest.fixture
def stream_constraint_factory():
    def create_stream_constraint(pressure: float):
        return PressureStreamConstraint(target_pressure=pressure)

    return create_stream_constraint


@pytest.fixture
def root_finding_strategy():
    return ScipyRootFindingStrategy()


@pytest.fixture
def search_strategy_factory():
    def create_search_strategy(tolerance: float = CONVERGENCE_TOLERANCE):
        return BinarySearchStrategy(tolerance=tolerance)

    return create_search_strategy
