from __future__ import annotations

from enum import Enum

from ecalc_neqsim_wrapper import neqsim
from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.fluid import EoSModel, FluidComposition
from libecalc.common.logger import logger


class NeqsimEoSModelType(Enum):
    SRK = neqsim.thermo.system.SystemSrkEos
    PR = neqsim.thermo.system.SystemPrEos
    GERG_SRK = neqsim.thermo.system.SystemSrkEos
    GERG_PR = neqsim.thermo.system.SystemPrEos


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


def map_fluid_composition_to_neqsim(fluid_composition: FluidComposition) -> dict[str, float]:
    component_dict = {}
    for component_name, value in fluid_composition.model_dump().items():
        if value is not None and value > 0:
            neqsim_name = _map_fluid_component_to_neqsim[component_name]
            component_dict[neqsim_name] = float(value)

    if len(component_dict) < 1:
        msg = "Can not run pvt calculations for fluid without components"
        logger.error(msg)
        raise EcalcError(title="Failed to create NeqSim fluid", message=msg)

    return component_dict


def map_eos_model_to_neqsim(ecalc_eos_model: EoSModel) -> NeqsimEoSModelType:
    try:
        return _map_eos_model_to_neqsim[ecalc_eos_model]
    except KeyError as e:
        raise EcalcError(title="Failed to create NeqSim fluid", message=str(e)) from e
