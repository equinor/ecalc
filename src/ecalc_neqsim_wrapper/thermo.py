from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Protocol, assert_never

from py4j.protocol import Py4JJavaError
from pydantic import BaseModel

from ecalc_neqsim_wrapper.components import COMPONENTS
from ecalc_neqsim_wrapper.exceptions import NeqsimComponentError, NeqsimPhaseError
from ecalc_neqsim_wrapper.java_service import get_neqsim_service
from ecalc_neqsim_wrapper.mappings import (
    NeqsimComposition,
    map_fluid_composition_from_neqsim,
    map_fluid_composition_to_neqsim,
)
from libecalc.common.decorators.capturer import Capturer
from libecalc.common.fluid import EoSModel, FluidComposition
from libecalc.common.logger import logger

STANDARD_TEMPERATURE_KELVIN = 288.15
STANDARD_PRESSURE_BARA = 1.01325

NEQSIM_MIXING_RULE = 2


class ThermodynamicSystem(Protocol):
    pass


class ThermodynamicOperations(Protocol):
    pass


class NeqsimFluidComponent(BaseModel):
    """
    A representation of a NeqSim Fluid Component. As a part of a composition. A
    gas or fluid, its amount and unit.
    """

    name: str
    total_fraction: float
    gas_fraction: float
    unit: str


class NeqsimFluidProperty(BaseModel):
    """
    A representation of a NeqSim Fluid Property. This is normally reused for the same composition
    for many different properties. It may contain numbers and strings.
    """

    name: str
    value: float | str
    unit: str


class NeqsimFluidState(BaseModel):
    """
    A representation of a NeqSim Fluid State for a given composition and properties
    """

    fluid_composition: list[NeqsimFluidComponent]
    fluid_properties: list[NeqsimFluidProperty]


class NeqsimFluid:
    def __init__(
        self,
        thermodynamic_system: ThermodynamicSystem,
        use_gerg: bool,
    ):
        """Should return self and not a new instance of class."""
        self._thermodynamic_system = thermodynamic_system
        self._use_gerg = use_gerg
        self._gerg_properties = (
            get_GERG2008_properties(thermodynamic_system=thermodynamic_system) if self._use_gerg else None
        )

    def json(self) -> str:
        """
        An attempt to jsonify a dump of the internal NeqSim state for a given composition and properties. If it fails, an empty
        string is returned.

        :return: the JSON representation of the Neqsim state, as an unformatted string
        """
        fluid_composition: list[NeqsimFluidComponent] = []
        fluid_properties: list[NeqsimFluidProperty] = []

        try:
            for string_vector in self._thermodynamic_system.createTable("ECALC_DUMP"):
                if "".join(string_vector).strip() == "" or string_vector[1] == "total":
                    # Ignored content, not useful. Headers and padding.
                    continue

                if str(string_vector[0]).strip() in COMPONENTS:
                    fluid_composition.append(
                        NeqsimFluidComponent(
                            name=string_vector[0],
                            total_fraction=string_vector[1],
                            gas_fraction=string_vector[2],
                            unit=string_vector[6],
                        )
                    )
                else:
                    fluid_properties.append(
                        NeqsimFluidProperty(name=string_vector[0], value=string_vector[2], unit=string_vector[6])
                    )

            neqsim_fluid_state = NeqsimFluidState(
                fluid_composition=fluid_composition, fluid_properties=fluid_properties
            )
            return neqsim_fluid_state.model_dump_json()

        except Exception as e:
            logger.warning(f"Failed to parse NeqSimState dump for JSON Serialization. Not critical: {e}")

        return ""

    @classmethod
    def create_thermo_system(
        cls,
        composition: FluidComposition,
        temperature_kelvin: float = STANDARD_TEMPERATURE_KELVIN,
        pressure_bara: float = STANDARD_PRESSURE_BARA,
        eos_model: EoSModel = EoSModel.SRK,
        mixing_rule: int = NEQSIM_MIXING_RULE,
    ) -> NeqsimFluid:
        """Initiates a NeqsimFluid that wraps both a Neqsim thermodynamic system and operations.

        TPflash: computes composition in each phase and densities
        init(3): computes all higher order thermodynamic properties, e.g. Cp/Cv,
        init(1): fugacities
        init(2): enough for CP/Cv
        Not necessary here because compressor.run-method does flash on inlet and outlet.

        :param composition: A dict with the composition of the thermodynamic_system components name: molar fraction.
        :param temperature_kelvin: The initial system temperature in Kelvin
        :param pressure_bara: The initial system pressure in absolute bar
        :param eos_model: The name of the underlying EOS model
        :param mixing_rule: The Neqsim mixing rule.
        :return:
        """
        use_gerg = "gerg" in eos_model.name.lower()

        composition = map_fluid_composition_to_neqsim(fluid_composition=composition)
        non_existing_components = [
            component for component, value in composition.items() if (component not in COMPONENTS) and (value > 0.0)
        ]
        if non_existing_components:
            raise ValueError(non_existing_components, " components does not exist in NeqSim")

        components, molar_fractions = zip(*composition.items())

        thermodynamic_system = cls._init_thermo_system(
            components=components,
            molar_fraction=molar_fractions,
            eos_model_type=eos_model,
            temperature_kelvin=temperature_kelvin,
            pressure_bara=pressure_bara,
            mixing_rule=mixing_rule,
        )

        # Since we are caching the java objects, they will contain the connection info to the java process (py4j).
        # That connection info might be outdated; clear the cache if that is the case.
        if thermodynamic_system._gateway_client.port != get_neqsim_service().get_neqsim_module()._gateway_client.port:
            cls._init_thermo_system.cache_clear()
            thermodynamic_system = cls._init_thermo_system(
                components=components,
                molar_fraction=molar_fractions,
                eos_model_type=eos_model,
                temperature_kelvin=temperature_kelvin,
                pressure_bara=pressure_bara,
                mixing_rule=mixing_rule,
            )

        return cls(thermodynamic_system=thermodynamic_system, use_gerg=use_gerg)

    @staticmethod
    def _get_eos_model(eos_model_type: EoSModel):
        neqsim_module = get_neqsim_service().get_neqsim_module()
        if eos_model_type == EoSModel.SRK:
            return neqsim_module.thermo.system.SystemSrkEos
        elif eos_model_type == EoSModel.PR:
            return neqsim_module.thermo.system.SystemPrEos
        elif eos_model_type == EoSModel.GERG_SRK:
            return neqsim_module.thermo.system.SystemSrkEos
        elif eos_model_type == EoSModel.GERG_PR:
            return neqsim_module.thermo.system.SystemPrEos
        else:
            assert_never(eos_model_type)

    @classmethod
    @lru_cache(maxsize=512)
    def _init_thermo_system(
        cls,
        components: list[str],
        molar_fraction: list[float],
        eos_model_type: EoSModel,
        temperature_kelvin: float,
        pressure_bara: float,
        mixing_rule: int,
    ) -> ThermodynamicSystem:
        """Initialize thermodynamic system"""
        use_gerg = "gerg" in eos_model_type.name.lower()

        eos_model = cls._get_eos_model(eos_model_type)

        thermodynamic_system = eos_model(float(temperature_kelvin), float(pressure_bara))

        [
            thermodynamic_system.addComponent(component, float(value))
            for component, value in zip(components, molar_fraction)
            if value > 0.0
        ]

        # Set a dummy rate as neqsim require a rate set to calculate physical properties
        thermodynamic_system.setTotalFlowRate(float(1000), "kg/hr")
        thermodynamic_system.setMixingRule(mixing_rule)

        thermodynamic_system = cls._tp_flash(thermodynamic_system=thermodynamic_system, use_gerg=use_gerg)
        return thermodynamic_system

    @property
    def volume(self) -> float:
        """Parameter needed for Schulz enthalpy calculations."""
        if self._use_gerg:
            raise NotImplementedError
        return self._thermodynamic_system.getVolume()

    @property
    def density(self) -> float:
        if self._use_gerg:
            return self._gerg_properties.density_kg_per_m3
        else:
            return self._thermodynamic_system.getDensity("kg/m3")

    @property
    def molar_mass(self) -> float:
        # NeqSim default return in unit kg/mol
        return self._thermodynamic_system.getMolarMass()

    @property
    def z(self) -> float:
        if self._use_gerg:
            return self._gerg_properties.z
        else:
            return self._thermodynamic_system.getZ()

    @property
    def enthalpy_joule_per_kg(self) -> float:
        if self._use_gerg:
            return self._gerg_properties.enthalpy_joule_per_kg
        else:
            return self._thermodynamic_system.getEnthalpy("J/kg")

    @property
    def kappa(self) -> float:
        """We use the non-real (ideal kappa) as used in NeqSim Compressor Chart modelling."""
        if self._use_gerg:
            return self._gerg_properties.kappa
        else:
            return self._thermodynamic_system.getGamma2()

    @property
    def temperature_kelvin(self) -> float:
        return self._thermodynamic_system.getTemperature("K")

    @property
    def pressure_bara(self) -> float:
        return self._thermodynamic_system.getPressure("bara")

    @cached_property
    def composition(self) -> FluidComposition:
        """Get the molar composition of the fluid.

        Returns:
            FluidComposition: The normalized molar composition of the fluid in ecalc format
        """
        # Get the molar composition and component names directly from the NeqSim API
        molar_composition = self._thermodynamic_system.getMolarComposition()
        component_names = self._thermodynamic_system.getComponentNames()

        # Build a dictionary with component names and molar fractions
        composition_dict = {}
        for i, name in enumerate(component_names):
            component_name = str(name)
            # Check if component is in the available components list
            if component_name not in COMPONENTS:
                raise NeqsimComponentError(component_name)

            composition_dict[component_name] = molar_composition[i]

        # Create a NeqsimComposition object
        neqsim_composition = NeqsimComposition.model_validate(composition_dict)
        # Map the Neqsim composition to ecalc format and ensure its normalized
        ecalc_composition = map_fluid_composition_from_neqsim(neqsim_composition).normalized()
        return ecalc_composition

    @cached_property
    def vapor_fraction_molar(self) -> float:
        if self._thermodynamic_system.hasPhaseType("gas"):
            phaseNumber = self._thermodynamic_system.getPhaseNumberOfPhase("gas")
            gasFraction = self._thermodynamic_system.getMoleFraction(phaseNumber)
            return gasFraction
        else:
            return 0.0

    @staticmethod
    def _tp_flash(thermodynamic_system: ThermodynamicSystem, use_gerg: bool) -> ThermodynamicSystem:
        """:param thermodynamic_system:
        :return:
        """
        thermodynamic_operations = (
            get_neqsim_service()
            .get_neqsim_module()
            .thermodynamicoperations.ThermodynamicOperations(thermodynamic_system)
        )
        thermodynamic_operations.TPflash()

        thermodynamic_system.init(3)
        thermodynamic_system.initProperties()

        return thermodynamic_system

    @staticmethod
    def _ph_flash(thermodynamic_system: ThermodynamicSystem, use_gerg: bool, enthalpy: float) -> ThermodynamicSystem:
        """:param thermodynamic_system:
        :param enthalpy:
        :param use_gerg:
        :return:
        """
        thermodynamic_operations = (
            get_neqsim_service()
            .get_neqsim_module()
            .thermodynamicoperations.ThermodynamicOperations(thermodynamic_system)
        )
        if use_gerg:
            enthalpy_joule = _get_enthalpy_joule_for_GERG2008_joule_per_kg(
                enthalpy=enthalpy, thermodynamic_system=thermodynamic_system
            )
            thermodynamic_operations.PHflashGERG2008(float(enthalpy_joule))
        else:
            thermodynamic_operations.PHflash(float(enthalpy), "J/kg")

        thermodynamic_system.init(3)
        thermodynamic_system.initProperties()

        return thermodynamic_system

    @staticmethod
    def _remove_liquid(thermodynamic_system: ThermodynamicSystem) -> ThermodynamicSystem:
        """Remove liquid part of thermodynamic_system, return new NeqsimFluid object with only gas part."""
        return thermodynamic_system.clone().phaseToSystem("gas")

    def copy(self) -> NeqsimFluid:
        return NeqsimFluid(thermodynamic_system=self._thermodynamic_system.clone(), use_gerg=self._use_gerg)

    @Capturer.capture_return_values(
        do_save_captured_content=False, output_directory=Path(os.getcwd()) / "captured_data" / "neqsim-ph"
    )
    def set_new_pressure_and_enthalpy(
        self, new_pressure: float, new_enthalpy_joule_per_kg: float, remove_liquid: bool = True
    ) -> NeqsimFluid:
        new_thermodynamic_system = self._thermodynamic_system.clone()
        new_thermodynamic_system.setPressure(float(new_pressure), "bara")

        new_thermodynamic_system = NeqsimFluid._ph_flash(
            thermodynamic_system=new_thermodynamic_system,
            enthalpy=new_enthalpy_joule_per_kg,
            use_gerg=self._use_gerg,
        )

        if remove_liquid:
            new_thermodynamic_system = NeqsimFluid._remove_liquid(thermodynamic_system=new_thermodynamic_system)

        return NeqsimFluid(thermodynamic_system=new_thermodynamic_system, use_gerg=self._use_gerg)

    @Capturer.capture_return_values(
        do_save_captured_content=False, output_directory=Path(os.getcwd()) / "captured_data" / "neqsim-tp"
    )
    def set_new_pressure_and_temperature(
        self, new_pressure_bara: float, new_temperature_kelvin: float, remove_liquid: bool = True
    ) -> NeqsimFluid:
        """Set new pressure and temperature and flash to find new state."""
        new_thermodynamic_system = self._thermodynamic_system.clone()
        new_thermodynamic_system.setPressure(float(new_pressure_bara), "bara")
        new_thermodynamic_system.setTemperature(float(new_temperature_kelvin), "K")

        new_thermodynamic_system = NeqsimFluid._tp_flash(
            thermodynamic_system=new_thermodynamic_system, use_gerg=self._use_gerg
        )

        if remove_liquid:
            new_thermodynamic_system = NeqsimFluid._remove_liquid(thermodynamic_system=new_thermodynamic_system)

        return NeqsimFluid(thermodynamic_system=new_thermodynamic_system, use_gerg=self._use_gerg)

    def display(self):
        self._thermodynamic_system.display()


@dataclass
class GERG2008FluidProperties:
    """Only added properties currently in use."""

    density_kg_per_m3: float
    z: float
    enthalpy_joule_per_kg: float
    kappa: float


def get_GERG2008_properties(thermodynamic_system: ThermodynamicSystem):
    """Getting the GERG2008 properties from NeqSim returns a list of the properties
    This method is to help mapping these to the correct names.
    """
    try:  # Using getPhase(0) instead of getPhase("gas") to handle dense fluids correctly
        gas_phase = thermodynamic_system.getPhase(0)
    except Py4JJavaError as e:
        msg = "Could not get gas phase. Make sure the fluid is specified correctly."
        raise NeqsimPhaseError(msg) from e
    gerg_properties = gas_phase.getProperties_GERG2008()
    gerg_density = gas_phase.getDensity_GERG2008()

    # Calculate enthalpy
    # Enthalpy in neqsim GERG is now J/mol (even though PHflashGERG2008 takes input enthalpy J!). Fixing this here for
    # now.
    enthalpy_joule_per_mol = gerg_properties[7]
    molar_mass_kg_per_mol = gas_phase.getMolarMass()
    enthalpy_joule_per_kg = enthalpy_joule_per_mol / molar_mass_kg_per_mol

    # Calculate kappa
    Cp = gerg_properties[10]
    R = 8.3144621
    # This will be relative (volume independent) as the number of moles in Cp will be divided by the number of moles
    # multiplied by R. Cp and Cv have default units Joule/(mol Kelvin)
    # NB: In neqsim, this is calculated as Cp / (Cp - R * number_of_moles), but when GERG is not used, the unit for Cp
    # is J/K, while with GERG neqsim has unit J/(K mol).
    kappa = Cp / (Cp - R)

    return GERG2008FluidProperties(
        density_kg_per_m3=gerg_density,
        z=gerg_properties[1],
        enthalpy_joule_per_kg=enthalpy_joule_per_kg,
        kappa=kappa,
    )


def _get_enthalpy_joule_for_GERG2008_joule_per_kg(enthalpy: float, thermodynamic_system: ThermodynamicSystem) -> float:
    return enthalpy * thermodynamic_system.getTotalNumberOfMoles() * thermodynamic_system.getMolarMass()


def mix_neqsim_streams(
    stream_composition_1: FluidComposition,
    stream_composition_2: FluidComposition,
    mass_rate_stream_1: float,
    mass_rate_stream_2: float,
    pressure: float,
    temperature: float,
    eos_model: EoSModel = EoSModel.SRK,
) -> tuple[FluidComposition, NeqsimFluid]:
    """Simplified mixing of two streams by component-wise molar balance.

    This mixing approach does not require thermodynamic equilibrium calculations.
    - It uses a specified resulting pressure and temperature.
    - Note: Same simplifications as previous ecalc mixing, but fixed calculation of composition.

    Args:
        stream_composition_1: FluidComposition object for the first stream.
        stream_composition_2: FluidComposition object for the second stream.
        mass_rate_stream_1: Mass flow rate of the first stream in kg/hr.
        mass_rate_stream_2: Mass flow rate of the second stream in kg/hr.
        pressure: The resulting pressure of the mixed stream in bara.
        temperature: The resulting temperature of the mixed stream in Kelvin.
        eos_model: The equation of state model to use for the resulting NeqsimFluid.

    Returns:
        tuple: A tuple containing the mixed FluidComposition and the resulting NeqsimFluid.
    """
    # Normalize input compositions
    normalized_comp_1 = stream_composition_1.normalized()
    normalized_comp_2 = stream_composition_2.normalized()

    molar_mass_1 = normalized_comp_1.molar_mass_mixture
    molar_mass_2 = normalized_comp_2.molar_mass_mixture

    molar_flow_rate_1 = mass_rate_stream_1 / molar_mass_1
    molar_flow_rate_2 = mass_rate_stream_2 / molar_mass_2

    component_molar_flow_rate: dict[str, float] = defaultdict(float)

    # eCalc composition dictionaries
    comp_1_dict = normalized_comp_1.model_dump()
    comp_2_dict = normalized_comp_2.model_dump()

    # Sum molar flow of each component across streams
    for composition, molar_rate in [(comp_1_dict, molar_flow_rate_1), (comp_2_dict, molar_flow_rate_2)]:
        for component, mole_fraction in composition.items():
            if mole_fraction > 0:  # Skip zero components
                component_molar_flow_rate[component] += molar_rate * mole_fraction

    # Calculate total molar flow and normalize to get mole fractions
    total_molar_flow = sum(component_molar_flow_rate.values())

    # Convert to composition dictionary with normalized mole fractions
    mixed_composition_dict = {
        component: moles / total_molar_flow for component, moles in component_molar_flow_rate.items()
    }

    # Create final FluidComposition object from our ecalc component dictionary
    # and normalize it
    ecalc_fluid_composition = FluidComposition.model_validate(mixed_composition_dict).normalized()

    # Create NeqsimFluid
    final_neqsim_fluid = NeqsimFluid.create_thermo_system(
        composition=ecalc_fluid_composition,
        temperature_kelvin=temperature,
        pressure_bara=pressure,
        eos_model=eos_model,
    )

    return ecalc_fluid_composition, final_neqsim_fluid
