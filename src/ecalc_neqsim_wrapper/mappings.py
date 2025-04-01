from __future__ import annotations

from pydantic import Field

from libecalc.common.errors.exceptions import EcalcError
from libecalc.common.fluid import EcalcBaseModel, FluidComposition
from libecalc.common.logger import logger


class NeqsimComposition(EcalcBaseModel):
    """Representation of a fluid composition in NeqSim format with named fields."""

    water: float = Field(0.0, ge=0.0)
    nitrogen: float = Field(0.0, ge=0.0)
    CO2: float = Field(0.0, ge=0.0)
    methane: float = Field(0.0, ge=0.0)
    ethane: float = Field(0.0, ge=0.0)
    propane: float = Field(0.0, ge=0.0)
    i_butane: float = Field(0.0, ge=0.0, alias="i-butane")
    n_butane: float = Field(0.0, ge=0.0, alias="n-butane")
    i_pentane: float = Field(0.0, ge=0.0, alias="i-pentane")
    n_pentane: float = Field(0.0, ge=0.0, alias="n-pentane")
    n_hexane: float = Field(0.0, ge=0.0, alias="n-hexane")

    def items(self) -> list[tuple[str, float]]:
        """Return a list of component names and their values."""
        return list(self.__dict__.items())


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


def map_fluid_composition_from_neqsim(neqsim_composition: NeqsimComposition) -> FluidComposition:
    """Map the fluid composition from NeqSim format to eCalc format.

    Args:
        neqsim_composition: A NeqsimComposition object with named fields matching NeqSim components

    Returns:
        FluidComposition: The molar composition in eCalc format
    """
    # The component names in NeqsimComposition are already matched to eCalc names
    # So we can directly validate with FluidComposition
    return FluidComposition.model_validate(neqsim_composition.model_dump())
