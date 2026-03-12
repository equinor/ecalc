"""Mapping between ecalc FluidComposition field names and thermopack component identifiers."""

from __future__ import annotations

import numpy as np

from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidComposition

# ecalc FluidComposition field name → thermopack component ID
ECALC_TO_THERMOPACK: dict[str, str] = {
    "water": "H2O",
    "nitrogen": "N2",
    "CO2": "CO2",
    "methane": "C1",
    "ethane": "C2",
    "propane": "C3",
    "i_butane": "IC4",
    "n_butane": "NC4",
    "i_pentane": "IC5",
    "n_pentane": "NC5",
    "n_hexane": "NC6",
}


def composition_to_thermopack(
    composition: FluidComposition,
) -> tuple[str, np.ndarray, list[str]]:
    """Convert ecalc FluidComposition to thermopack inputs.

    Only includes components with non-zero mole fractions.

    Args:
        composition: Normalized ecalc FluidComposition.

    Returns:
        Tuple of:
        - component_string: Comma-separated thermopack component IDs (e.g. "N2,CO2,C1")
        - mole_fractions: numpy array of normalized mole fractions (same order)
        - ecalc_names: list of ecalc field names for reverse mapping
    """
    comp_data = composition.model_dump()

    tp_ids: list[str] = []
    fractions: list[float] = []
    ecalc_names: list[str] = []

    for ecalc_name, tp_id in ECALC_TO_THERMOPACK.items():
        value = comp_data.get(ecalc_name, 0.0)
        if value > 0.0:
            tp_ids.append(tp_id)
            fractions.append(value)
            ecalc_names.append(ecalc_name)

    z = np.array(fractions)
    z = z / z.sum()  # renormalize active components

    component_string = ",".join(tp_ids)
    return component_string, z, ecalc_names
