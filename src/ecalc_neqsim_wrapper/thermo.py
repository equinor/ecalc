from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple, Union

from libecalc import dto
from libecalc.common.decorators.capturer import Capturer
from libecalc.common.logger import logger
from libecalc.dto import FluidComposition
from libecalc.dto.types import EoSModel
from py4j.protocol import Py4JJavaError
from pydantic import BaseModel

from ecalc_neqsim_wrapper import neqsim
from ecalc_neqsim_wrapper.components import COMPONENTS
from ecalc_neqsim_wrapper.exceptions import NeqsimPhaseError
from ecalc_neqsim_wrapper.mappings import (
    NeqsimEoSModelType,
    _map_fluid_component_from_neqsim,
    map_eos_model_to_neqsim,
    map_fluid_composition_to_neqsim,
)

STANDARD_TEMPERATURE_KELVIN = 288.15
STANDARD_PRESSURE_BARA = 1.01325

NEQSIM_MIXING_RULE = 2

ThermodynamicSystem = neqsim.thermo.system.SystemEos
ThermodynamicOperations = neqsim.thermodynamicOperations.ThermodynamicOperations


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
    value: Union[float, str]
    unit: str


class NeqsimFluidState(BaseModel):
    """
    A representation of a NeqSim Fluid State for a given composition and properties
    """

    fluid_composition: List[NeqsimFluidComponent]
    fluid_properties: List[NeqsimFluidProperty]


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
        fluid_composition: List[NeqsimFluidComponent] = []
        fluid_properties: List[NeqsimFluidProperty] = []

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
            return neqsim_fluid_state.json()

        except Exception as e:
            logger.warning(f"Failed to parse NeqSimState dump for JSON Serialization. Not critical: {e}")

        return ""

    @classmethod
    def create_thermo_system(
        cls,
        composition: dto.FluidComposition,
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
        eos_model = map_eos_model_to_neqsim(eos_model)
        non_existing_components = [
            component for component, value in composition.items() if (component not in COMPONENTS) and (value > 0.0)
        ]
        if non_existing_components:
            raise ValueError(non_existing_components, " components does not exist in NeqSim")

        components, molar_fractions = zip(*composition.items())

        thermodynamic_system = NeqsimFluid._init_thermo_system(
            components=components,
            molar_fraction=molar_fractions,
            eos_model=eos_model,
            temperature_kelvin=temperature_kelvin,
            pressure_bara=pressure_bara,
            mixing_rule=mixing_rule,
        )

        return NeqsimFluid(thermodynamic_system=thermodynamic_system, use_gerg=use_gerg)

    @staticmethod
    @lru_cache(maxsize=512)
    def _init_thermo_system(
        components: List[str],
        molar_fraction: List[float],
        eos_model: NeqsimEoSModelType,
        temperature_kelvin: float,
        pressure_bara: float,
        mixing_rule: int,
    ) -> ThermodynamicSystem:
        """Initialize thermodynamic system"""
        use_gerg = "gerg" in eos_model.name.lower()

        thermodynamic_system = eos_model.value(float(temperature_kelvin), float(pressure_bara))

        [
            thermodynamic_system.addComponent(component, float(value))
            for component, value in zip(components, molar_fraction)
            if value > 0.0
        ]

        # Set a dummy rate as neqsim require a rate set to calculate physical properties
        thermodynamic_system.setTotalFlowRate(float(1000), "kg/hr")
        thermodynamic_system.setMixingRule(mixing_rule)

        thermodynamic_system = NeqsimFluid._tp_flash(thermodynamic_system=thermodynamic_system, use_gerg=use_gerg)
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

    @staticmethod
    def _tp_flash(thermodynamic_system: ThermodynamicSystem, use_gerg: bool) -> ThermodynamicSystem:
        """:param thermodynamic_system:
        :return:
        """
        thermodynamic_operations = ThermodynamicOperations(thermodynamic_system)
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
        thermodynamic_operations = ThermodynamicOperations(thermodynamic_system)
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
) -> Tuple[dto.FluidComposition, NeqsimFluid]:
    """Mixing two streams (NeqsimFluids) with same pressure and temperature."""

    composition_dict: Dict[str, float] = {}

    stream_1 = NeqsimFluid.create_thermo_system(
        composition=stream_composition_1,
        temperature_kelvin=temperature,
        pressure_bara=pressure,
        eos_model=eos_model,
    )

    stream_2 = NeqsimFluid.create_thermo_system(
        composition=stream_composition_2,
        temperature_kelvin=temperature,
        pressure_bara=pressure,
        eos_model=eos_model,
    )

    mol_per_hour_1 = mass_rate_stream_1 / stream_1.molar_mass
    mol_per_hour_2 = mass_rate_stream_2 / stream_2.molar_mass

    fraction_1 = mol_per_hour_1 / (mol_per_hour_1 + mol_per_hour_2)
    fraction_2 = mol_per_hour_2 / (mol_per_hour_1 + mol_per_hour_2)

    for stream, fraction in zip((stream_1, stream_2), (fraction_1, fraction_2)):
        for i in range(stream._thermodynamic_system.getNumberOfComponents()):
            composition_name = stream._thermodynamic_system.getComponent(i).getComponentName()
            composition_moles = fraction * stream._thermodynamic_system.getComponent(i).getNumberOfmoles()
            if composition_name in composition_dict:
                composition_dict[composition_name] = composition_dict[composition_name] + composition_moles
            else:
                composition_dict[composition_name] = composition_moles

    ecalc_fluid_composition = dto.FluidComposition.parse_obj(
        {_map_fluid_component_from_neqsim[key]: value for (key, value) in composition_dict.items()}
    )

    return (
        ecalc_fluid_composition,
        NeqsimFluid.create_thermo_system(
            composition=ecalc_fluid_composition,
            temperature_kelvin=temperature,
            pressure_bara=pressure,
            eos_model=eos_model,
        ),
    )
