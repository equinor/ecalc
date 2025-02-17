from libecalc.common.component_type import ComponentType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesRate
from libecalc.domain.emission.emission_intensity import EmissionIntensity
from libecalc.domain.energy import EnergyComponent
from libecalc.domain.infrastructure.energy_components.installation.installation import Installation
from libecalc.dto.component_graph import ComponentGraph
from libecalc.presentation.json_result.result.emission import EmissionIntensityResult, PartialEmissionResult


class Asset(EnergyComponent):
    def __init__(
        self,
        name: str,
        installations: list[Installation],
    ):
        self.name = name
        self.installations = installations
        self.component_type = ComponentType.ASSET

    @property
    def id(self):
        return generate_id(self.name)

    def is_fuel_consumer(self) -> bool:
        return True

    def is_electricity_consumer(self) -> bool:
        # Should maybe be True if power from shore?
        return False

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return True

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

    def get_graph(self) -> ComponentGraph:
        graph = ComponentGraph()
        graph.add_node(self)
        for installation in self.installations:
            graph.add_subgraph(installation.get_graph())
            graph.add_edge(self.id, installation.id)

        return graph

    @staticmethod
    def calculate_emission_intensity(
        hydrocarbon_export_rate: TimeSeriesRate,
        emissions: dict[str, PartialEmissionResult],
    ) -> list[EmissionIntensityResult]:
        hydrocarbon_export_cumulative = hydrocarbon_export_rate.to_volumes().cumulative()
        emission_intensities = []
        for key in emissions:
            cumulative_rate_kg = emissions[key].rate.to_volumes().to_unit(Unit.KILO).cumulative()
            intensity = EmissionIntensity(
                emission_cumulative=cumulative_rate_kg,
                hydrocarbon_export_cumulative=hydrocarbon_export_cumulative,
            )
            intensity_sm3 = intensity.calculate_cumulative()
            intensity_periods_sm3 = intensity.calculate_for_periods()

            emission_intensities.append(
                EmissionIntensityResult(
                    name=emissions[key].name,
                    periods=emissions[key].periods,
                    intensity_sm3=intensity_sm3,
                    intensity_boe=intensity_sm3.to_unit(Unit.KG_BOE),
                    intensity_periods_sm3=intensity_periods_sm3,
                    intensity_periods_boe=intensity_periods_sm3.to_unit(Unit.KG_BOE),
                )
            )
        return emission_intensities
