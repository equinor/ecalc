from __future__ import annotations

from typing import Dict, List, Union

import numpy as np
from libecalc import dto
from libecalc.common.exceptions import EcalcError
from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.dto.types import EoSModel
from neqsim_ecalc_wrapper import NeqsimEoSModelType, NeqsimFluid
from numpy.typing import NDArray

_map_eos_model_to_neqsim = {
    EoSModel.SRK: NeqsimEoSModelType.SRK,
    EoSModel.PR: NeqsimEoSModelType.PR,
    EoSModel.GERG_SRK: NeqsimEoSModelType.GERG_SRK,
    EoSModel.GERG_PR: NeqsimEoSModelType.GERG_PR,
}

_map_fluid_component_to_neqsim = {
    "water": "water",
    "nitrogen": "nitrogen",
    "CO2": "CO2",
    "methane": "methane",
    "ethane": "ethane",
    "propane": "propane",
    "i_butane": "i-butane",
    "n_butane": "n-butane",
    "i_pentane": "i-pentane",
    "n_pentane": "n-pentane",
    "n_hexane": "n-hexane",
}

_map_fluid_component_from_neqsim = {
    "water": "water",
    "nitrogen": "nitrogen",
    "CO2": "CO2",
    "methane": "methane",
    "ethane": "ethane",
    "propane": "propane",
    "i-butane": "i_butane",
    "n-butane": "n_butane",
    "i-pentane": "i_pentane",
    "n-pentane": "n_pentane",
    "n-hexane": "n_hexane",
}


class FluidStream:
    """Currently just a dataclass with a set composition.

    Keep as separate layer until having different initialization options to set composition
    """

    def __init__(
        self,
        fluid_model: dto.FluidModel,
        pressure_bara: float = UnitConstants.STANDARD_PRESSURE_BARA,
        temperature_kelvin: float = UnitConstants.STANDARD_TEMPERATURE_KELVIN,
    ):
        self.fluid_model = fluid_model

        if not temperature_kelvin > 0:
            raise ValueError("FluidStream temperature needs to be above 0.")
        if not pressure_bara > 0:
            raise ValueError("FluidStream pressure needs to be above 0.")

        self._neqsim_fluid_stream = NeqsimFluid.create_thermo_system(
            composition=self._map_fluid_composition_to_neqsim(fluid_composition=self.fluid_model.composition),
            temperature_kelvin=temperature_kelvin,
            pressure_bara=pressure_bara,
            eos_model=_map_eos_model_to_neqsim[self.fluid_model.eos_model],
        )

        if (
            pressure_bara == UnitConstants.STANDARD_PRESSURE_BARA
            and temperature_kelvin == UnitConstants.STANDARD_TEMPERATURE_KELVIN
        ):
            self.standard_conditions_density = self._neqsim_fluid_stream.density
            self.molar_mass_kg_per_mol = self._neqsim_fluid_stream.molar_mass
        else:
            _neqsim_fluid_at_standard_conditions = NeqsimFluid.create_thermo_system(
                composition=self._map_fluid_composition_to_neqsim(fluid_composition=self.fluid_model.composition),
                temperature_kelvin=UnitConstants.STANDARD_TEMPERATURE_KELVIN,
                pressure_bara=UnitConstants.STANDARD_PRESSURE_BARA,
                eos_model=_map_eos_model_to_neqsim[self.fluid_model.eos_model],
            )

            self.standard_conditions_density = _neqsim_fluid_at_standard_conditions.density
            self.molar_mass_kg_per_mol = _neqsim_fluid_at_standard_conditions.molar_mass

    @property
    def pressure_bara(self) -> float:
        return self._neqsim_fluid_stream.pressure_bara

    @property
    def temperature_kelvin(self) -> float:
        return self._neqsim_fluid_stream.temperature_kelvin

    @property
    def kappa(self) -> float:
        return self._neqsim_fluid_stream.kappa

    @property
    def density(self) -> float:
        return self._neqsim_fluid_stream.density

    @property
    def z(self) -> float:
        return self._neqsim_fluid_stream.z

    @staticmethod
    def _map_fluid_composition_to_neqsim(fluid_composition: dto.FluidComposition) -> Dict[str, float]:
        component_dict = {}
        for component_name, value in fluid_composition.dict().items():
            if value is not None and value > 0:
                neqsim_name = _map_fluid_component_to_neqsim[component_name]
                component_dict[neqsim_name] = float(value)

        if len(component_dict) < 1:
            msg = "Can not run pvt calculations for fluid without components"
            logger.error(msg)
            raise EcalcError(msg)

        return component_dict

    def standard_to_mass_rate(
        self, standard_rates: Union[NDArray[np.float64], float]
    ) -> Union[NDArray[np.float64], float]:
        """Sm3/day to kg/h. Standard conditions are 15C at 1atm = 1.01325 bara."""
        mass_rate_kg_per_hour = standard_rates * self.standard_conditions_density / UnitConstants.HOURS_PER_DAY
        if isinstance(mass_rate_kg_per_hour, np.ndarray):
            return np.array(mass_rate_kg_per_hour)
        else:
            return float(mass_rate_kg_per_hour)

    def mass_rate_to_standard_rate(
        self, mass_rate_kg_per_hour: Union[NDArray[np.float64], float]
    ) -> Union[NDArray[np.float64], float]:
        """Convert mass rate from kg/h to Sm3/day.

        Args:
            mass_rate_kg_per_hour: One or more mass rates to convert [kg/h]

        Returns:
            Mass rates in Sm3/day

        """
        standard_rate_kg_per_hour = (
            mass_rate_kg_per_hour / self.standard_conditions_density * UnitConstants.HOURS_PER_DAY
        )
        if isinstance(standard_rate_kg_per_hour, np.ndarray):
            return np.array(standard_rate_kg_per_hour)
        else:
            return float(standard_rate_kg_per_hour)

    def get_fluid_stream(self, pressure_bara: float, temperature_kelvin: float) -> FluidStream:
        """Return a fluid stream for given pressure and temperature

        Args:
            pressure_bara: Pressure setpoint for fluid stream [bara]
            temperature_kelvin: Temperature setpoint for fluid stream [kelvin]

        Returns:
            Fluid stream at set temperature and pressure

        """
        return FluidStream(
            fluid_model=self.fluid_model, pressure_bara=pressure_bara, temperature_kelvin=temperature_kelvin
        )

    def get_fluid_streams(
        self, pressure_bara: NDArray[np.float64], temperature_kelvin: NDArray[np.float64]
    ) -> List[FluidStream]:
        """Get multiple fluid streams from multiple temperatures and pressures

        Args:
            pressure_bara: array of pressures [bara]
            temperature_kelvin: array of temperatures [kelvin]

        Returns:
            List of fluid streams at set temperatures and pressures

        """
        streams = [
            self.get_fluid_stream(pressure_bara=pressure_value, temperature_kelvin=temperature_value)
            for pressure_value, temperature_value in zip(pressure_bara, temperature_kelvin)
        ]

        return streams

    def set_new_pressure_and_temperature(
        self, new_pressure_bara: float, new_temperature_kelvin: float, remove_liquid: bool = True
    ) -> FluidStream:
        new_fluid_stream = self.copy()
        new_fluid_stream._neqsim_fluid_stream = new_fluid_stream._neqsim_fluid_stream.set_new_pressure_and_temperature(
            new_pressure_bara=new_pressure_bara,
            new_temperature_kelvin=new_temperature_kelvin,
            remove_liquid=remove_liquid,
        )
        return new_fluid_stream

    def set_new_pressure_and_enthalpy_change(
        self, new_pressure: float, enthalpy_change_joule_per_kg: float, remove_liquid: bool = True
    ) -> FluidStream:
        new_fluid_stream = self.copy()
        new_fluid_stream._neqsim_fluid_stream = new_fluid_stream._neqsim_fluid_stream.set_new_pressure_and_enthalpy(
            new_pressure=new_pressure,
            new_enthalpy_joule_per_kg=new_fluid_stream._neqsim_fluid_stream.enthalpy_joule_per_kg
            + enthalpy_change_joule_per_kg,
            remove_liquid=remove_liquid,
        )
        return new_fluid_stream

    def copy(self) -> FluidStream:
        return FluidStream(
            fluid_model=self.fluid_model, pressure_bara=self.pressure_bara, temperature_kelvin=self.temperature_kelvin
        )

    def mix_in_stream(
        self,
        other_fluid_stream: FluidStream,
        self_mass_rate: float,
        other_mass_rate: float,
        pressure_bara: float,
        temperature_kelvin: float,
    ) -> FluidStream:
        """Mix in a new fluid stream and get combined fluid stream

        Args:
            other_fluid_stream: Fluid stream to be mixed in
            self_mass_rate: Mass rate of the current fluid stream
            other_mass_rate: Mass rate of the "mix-in" fluid stream
            pressure_bara: Pressure of the fluid streams (Must be equal for both streams)
            temperature_kelvin: Temperature of the fluid streams ( Must be equal for both streams)

        Returns:
            New fluid stream with mixed in fluid

        """
        new_fluid_stream = self.copy()
        composition_dict, new_fluid_stream._neqsim_fluid_stream = new_fluid_stream._neqsim_fluid_stream.mix_streams(
            stream_1=new_fluid_stream._neqsim_fluid_stream,
            stream_2=other_fluid_stream._neqsim_fluid_stream,
            mass_rate_stream_1=self_mass_rate,
            mass_rate_stream_2=other_mass_rate,
            pressure=pressure_bara,
            temperature=temperature_kelvin,
            eos_model=_map_eos_model_to_neqsim[new_fluid_stream.fluid_model.eos_model],
        )

        new_composition_dict = {
            _map_fluid_component_from_neqsim[key]: value for (key, value) in composition_dict.items()
        }

        new_fluid_stream.fluid_model.composition = dto.FluidComposition.parse_obj(new_composition_dict)

        return new_fluid_stream
