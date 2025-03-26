"""
Constants and properties used in thermodynamic calculations.
"""

from pydantic import BaseModel, Field


class ComponentProperties(BaseModel):
    """Properties for a single component including critical properties and molecular weight."""

    critical_temperature_k: float = Field(..., alias="Tc")  # K
    critical_pressure_bara: float = Field(..., alias="Pc")  # bara
    acentric_factor: float = Field(..., alias="omega")
    molecular_weight_kg_per_mol: float


class ThermodynamicConstants:
    """Constants used in thermodynamic calculations."""

    # Gas constant
    R_J_PER_MOL_K = 8.31446261815324  # J/(mol·K)

    # Component properties combining critical properties and molecular weights
    COMPONENTS: dict[str, ComponentProperties] = {
        "water": ComponentProperties(Tc=647.3, Pc=221.2, omega=0.344, molecular_weight_kg_per_mol=0.01801534),
        "nitrogen": ComponentProperties(Tc=126.2, Pc=33.9, omega=0.039, molecular_weight_kg_per_mol=0.02801340),
        "CO2": ComponentProperties(Tc=304.1, Pc=73.8, omega=0.239, molecular_weight_kg_per_mol=0.04400995),
        "methane": ComponentProperties(Tc=190.4, Pc=46.0, omega=0.011, molecular_weight_kg_per_mol=0.01604246),
        "ethane": ComponentProperties(Tc=305.4, Pc=48.8, omega=0.099, molecular_weight_kg_per_mol=0.03006904),
        "propane": ComponentProperties(Tc=369.8, Pc=42.5, omega=0.153, molecular_weight_kg_per_mol=0.04409562),
        "i_butane": ComponentProperties(Tc=408.2, Pc=36.5, omega=0.183, molecular_weight_kg_per_mol=0.05812220),
        "n_butane": ComponentProperties(Tc=425.2, Pc=38.0, omega=0.199, molecular_weight_kg_per_mol=0.05812220),
        "i_pentane": ComponentProperties(Tc=460.4, Pc=33.9, omega=0.227, molecular_weight_kg_per_mol=0.07214878),
        "n_pentane": ComponentProperties(Tc=469.7, Pc=33.7, omega=0.251, molecular_weight_kg_per_mol=0.07214878),
        "n_hexane": ComponentProperties(Tc=507.5, Pc=30.1, omega=0.299, molecular_weight_kg_per_mol=0.08617536),
    }

    @classmethod
    def get_component_molecular_weight(cls, component: str) -> float:
        """Retrieve the molecular weight for a given component."""
        try:
            return cls.COMPONENTS[component].molecular_weight_kg_per_mol
        except KeyError:
            raise ValueError(f"Molecular weight for component '{component}' is not defined.") from None
