from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

from libecalc.process.fluid_stream.fluid_model import FluidModel
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.thermodynamics.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
)


class RatesAndHeads(NamedTuple):
    rates_m3_per_hour: list[float]
    heads_joule_per_kg: list[float]


def rates_and_heads_from_operating_points(
    fluid_model: FluidModel,
    fluid_service: FluidService,
    standard_rates: list[float],
    inlet_temperature: float,
    inlet_pressure: list[float],
    outlet_pressure: list[float],
    polytropic_efficiency: float,
) -> RatesAndHeads:
    """Actual inlet volume rates [Am3/h] and polytropic heads [J/kg] for operating points given in standard rates."""
    inlet_streams = [
        fluid_service.create_stream_from_standard_rate(
            fluid_model=fluid_model,
            pressure_bara=pressure,
            temperature_kelvin=inlet_temperature,
            standard_rate_m3_per_day=rate,
        )
        for rate, pressure in zip(standard_rates, inlet_pressure)
    ]

    def efficiency_as_function_of_rate_and_head(
        rates: NDArray[np.float64], heads: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        return np.full_like(rates, fill_value=polytropic_efficiency, dtype=float)

    enthalpy_change_joule_per_kg, efficiency = calculate_enthalpy_change_head_iteration(
        inlet_streams=inlet_streams,
        outlet_pressure=np.asarray(outlet_pressure),
        polytropic_efficiency_vs_rate_and_head_function=efficiency_as_function_of_rate_and_head,
        fluid_service=fluid_service,
    )

    heads = np.atleast_1d(enthalpy_change_joule_per_kg * efficiency).astype(float).tolist()
    rates = np.asarray([stream.volumetric_rate_m3_per_hour for stream in inlet_streams]).astype(float).tolist()
    return RatesAndHeads(rates_m3_per_hour=rates, heads_joule_per_kg=heads)
