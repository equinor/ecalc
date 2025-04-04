from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from ecalc_neqsim_wrapper import NeqsimFluid
from ecalc_neqsim_wrapper.thermo import mix_neqsim_streams
from libecalc.common.fluid import FluidModel
from libecalc.common.units import UnitConstants


class FluidStream:
    """Fluid interface used in eCalc compressor train simulation

    TODO:
        - [x] Remove NeqSimFluid as class member
        - [ ] Remove connections to NeqSimFluid
        - [ ] Separate init methods based on config. To enable eCalc to be agnostick EoS package backend (NeqSim, ML, thermo(?))
    """

    def __init__(
        self,
        fluid_model: FluidModel,
        pressure_bara: float = UnitConstants.STANDARD_PRESSURE_BARA,
        temperature_kelvin: float = UnitConstants.STANDARD_TEMPERATURE_KELVIN,
        existing_fluid: NeqsimFluid | None = None,
    ):
        """

        Args:
            fluid_model: Describes fluid composition and EoS model
            pressure_bara: Pressure of fluid [bara]
            temperature_kelvin: Temperature of fluid [K]
            existing_fluid: Initialize FluidStream from an existing (NeqSim) fluid. Warning: Be mindful of keeping fluid_model and existing fluid consistent. If not the fluid properties may be incorrect.
        """
        self.fluid_model = fluid_model

        if not temperature_kelvin > 0:
            raise ValueError("FluidStream temperature needs to be above 0.")
        if not pressure_bara > 0:
            raise ValueError("FluidStream pressure needs to be above 0.")
        if existing_fluid is None:
            _neqsim_fluid_stream = NeqsimFluid.create_thermo_system(
                composition=self.fluid_model.composition,
                temperature_kelvin=temperature_kelvin,
                pressure_bara=pressure_bara,
                eos_model=self.fluid_model.eos_model,
            )
        else:
            _neqsim_fluid_stream = existing_fluid

        self._pressure_bara = _neqsim_fluid_stream.pressure_bara
        self._temperature_kelvin = _neqsim_fluid_stream.temperature_kelvin
        self._kappa = _neqsim_fluid_stream.kappa
        self._density = _neqsim_fluid_stream.density
        self._z = _neqsim_fluid_stream.z
        self._enthalpy_joule_per_kg = _neqsim_fluid_stream.enthalpy_joule_per_kg

        if (
            self._pressure_bara == UnitConstants.STANDARD_PRESSURE_BARA
            and self._temperature_kelvin == UnitConstants.STANDARD_TEMPERATURE_KELVIN
        ):
            self.standard_conditions_density = _neqsim_fluid_stream.density
            self.molar_mass_kg_per_mol = _neqsim_fluid_stream.molar_mass
        else:
            _neqsim_fluid_at_standard_conditions = NeqsimFluid.create_thermo_system(
                composition=self.fluid_model.composition,
                temperature_kelvin=UnitConstants.STANDARD_TEMPERATURE_KELVIN,
                pressure_bara=UnitConstants.STANDARD_PRESSURE_BARA,
                eos_model=self.fluid_model.eos_model,
            )
            self.standard_conditions_density = _neqsim_fluid_at_standard_conditions.density
            self.molar_mass_kg_per_mol = _neqsim_fluid_stream.molar_mass

    @property
    def pressure_bara(self) -> float:
        return self._pressure_bara

    @property
    def temperature_kelvin(self) -> float:
        return self._temperature_kelvin

    @property
    def kappa(self) -> float:
        return self._kappa

    @property
    def density(self) -> float:
        return self._density

    @property
    def z(self) -> float:
        return self._z

    @property
    def enthalpy_joule_per_kg(self) -> float:
        return self._enthalpy_joule_per_kg

    def standard_rate_to_mass_rate(self, standard_rates: NDArray[np.float64] | float) -> NDArray[np.float64] | float:
        """Convert standard rate [Sm3/day] to mass rate [kg/h].

        Use standard conditions are 15C at 1atm = 1.01325 bara for fluid density.

        Args:
            standard_rates:list or single rate(s) to convert [Sm3/day]

        Returns:
           list or single standard rate(s) [kg/h]
        """
        mass_rate_kg_per_hour = standard_rates * self.standard_conditions_density / UnitConstants.HOURS_PER_DAY
        if isinstance(mass_rate_kg_per_hour, np.ndarray):
            return np.array(mass_rate_kg_per_hour)
        else:
            return float(mass_rate_kg_per_hour)

    def mass_rate_to_standard_rate(
        self, mass_rate_kg_per_hour: NDArray[np.float64] | float
    ) -> NDArray[np.float64] | float:
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
    ) -> list[FluidStream]:
        """Get multiple fluid streams from multiple temperatures and pressures

        Args:
            pressure_bara: array of pressures [bara]
            temperature_kelvin: array of temperatures [K]

        Returns:
           list of fluid streams at set temperatures and pressures

        """
        streams = [
            self.get_fluid_stream(pressure_bara=pressure_value, temperature_kelvin=temperature_value)
            for pressure_value, temperature_value in zip(pressure_bara, temperature_kelvin)
        ]

        return streams

    def set_new_pressure_and_temperature(
        self, new_pressure_bara: float, new_temperature_kelvin: float, remove_liquid: bool = True
    ) -> FluidStream:
        """Get a new fluid with changed pressure and temperature.

        This is a wrapper of a TP-flash

        Args:
            new_pressure_bara: Pressure setpoint of new fluid [bara]
            new_temperature_kelvin: Temperature setpoint of new fluid [K]
            remove_liquid: If true the new fluid will be forced to be single phase (Gas), defaults to true

        Returns:
            New fluid stream flashed to a new temperature and pressure setpoint

        """
        fluid_stream = NeqsimFluid.create_thermo_system(
            composition=self.fluid_model.composition,
            temperature_kelvin=self.temperature_kelvin,
            pressure_bara=self.pressure_bara,
            eos_model=self.fluid_model.eos_model,
        )

        fluid_stream = fluid_stream.set_new_pressure_and_temperature(
            new_pressure_bara=new_pressure_bara,
            new_temperature_kelvin=new_temperature_kelvin,
            remove_liquid=remove_liquid,
        )
        return FluidStream(
            existing_fluid=fluid_stream,
            fluid_model=self.fluid_model,
        )

    def set_new_pressure_and_enthalpy_change(
        self, new_pressure: float, enthalpy_change_joule_per_kg: float, remove_liquid: bool = True
    ) -> FluidStream:
        """Get a new fluid with changed pressure and changed enthalpy.

        This is a wrapper of a PH-flash

        Args:
            new_pressure: Pressure setpoint of new fluid [bara]
            enthalpy_change_joule_per_kg: Change in enthalpy performed on new fluid [J/kg]
            remove_liquid: If true the new fluid will be forced to be single phase (Gas), defaults to true

        Returns:
            Mew fluid stream flashed to a new pressure and changed enthalpy

        """
        fluid_stream = NeqsimFluid.create_thermo_system(
            composition=self.fluid_model.composition,
            temperature_kelvin=self.temperature_kelvin,
            pressure_bara=self.pressure_bara,
            eos_model=self.fluid_model.eos_model,
        )

        fluid_stream = fluid_stream.set_new_pressure_and_enthalpy(
            new_pressure=new_pressure,
            new_enthalpy_joule_per_kg=fluid_stream.enthalpy_joule_per_kg + enthalpy_change_joule_per_kg,
            remove_liquid=remove_liquid,
        )
        return FluidStream(existing_fluid=fluid_stream, fluid_model=self.fluid_model)

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

        if self.fluid_model.eos_model != other_fluid_stream.fluid_model.eos_model:
            raise ValueError(
                f"Mixing of fluids with different EoS Models is not supported. Got '{self.fluid_model.eos_model}' and '{other_fluid_stream.fluid_model.eos_model}"
            )

        if (self.pressure_bara != pressure_bara) or (other_fluid_stream.pressure_bara != pressure_bara):
            raise ValueError(
                f"Can not mix fluids at different pressures. The fluids are at {self.pressure_bara} bara and '{other_fluid_stream.pressure_bara}' bara and were attempted to be mixed at {pressure_bara} bara"
            )

        mixed_fluid_composition, mixed_neqsim_fluid_stream = mix_neqsim_streams(
            stream_composition_1=self.fluid_model.composition,
            stream_composition_2=other_fluid_stream.fluid_model.composition,
            mass_rate_stream_1=self_mass_rate,
            mass_rate_stream_2=other_mass_rate,
            pressure=pressure_bara,
            temperature=temperature_kelvin,
            eos_model=self.fluid_model.eos_model,
        )

        return FluidStream(
            existing_fluid=mixed_neqsim_fluid_stream,
            fluid_model=FluidModel(composition=mixed_fluid_composition, eos_model=self.fluid_model.eos_model),
        )
