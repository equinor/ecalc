"""
Constants and properties used in thermodynamic calculations.
"""

from libecalc.common.ddd import value_object


@value_object
class ComponentProperties:
    """Properties for a single component including critical properties and molecular weight."""

    critical_temperature_k: float
    critical_pressure_bara: float
    acentric_factor: float
    molecular_weight_kg_per_mol: float


class ThermodynamicConstants:
    """Constants used in thermodynamic calculations."""

    # Gas constant
    R_J_PER_MOL_K = 8.31446261815324  # J/(mol·K)

    # Vapor fraction threshold - fluids at or above this are considered pure gas.
    # Used to skip liquid removal operations when fluid is essentially all vapor.
    # The 0.9999 tolerance accounts for floating point precision and trace liquid.
    PURE_VAPOR_THRESHOLD = 0.9999

    # Component properties combining critical properties and molecular weights
    COMPONENTS: dict[str, ComponentProperties] = {
        "water": ComponentProperties(
            critical_temperature_k=647.3,
            critical_pressure_bara=221.2,
            acentric_factor=0.344,
            molecular_weight_kg_per_mol=0.01801534,
        ),
        "nitrogen": ComponentProperties(
            critical_temperature_k=126.2,
            critical_pressure_bara=33.9,
            acentric_factor=0.039,
            molecular_weight_kg_per_mol=0.02801340,
        ),
        "CO2": ComponentProperties(
            critical_temperature_k=304.1,
            critical_pressure_bara=73.8,
            acentric_factor=0.239,
            molecular_weight_kg_per_mol=0.04400995,
        ),
        "methane": ComponentProperties(
            critical_temperature_k=190.4,
            critical_pressure_bara=46.0,
            acentric_factor=0.011,
            molecular_weight_kg_per_mol=0.01604246,
        ),
        "ethane": ComponentProperties(
            critical_temperature_k=305.4,
            critical_pressure_bara=48.8,
            acentric_factor=0.099,
            molecular_weight_kg_per_mol=0.03006904,
        ),
        "propane": ComponentProperties(
            critical_temperature_k=369.8,
            critical_pressure_bara=42.5,
            acentric_factor=0.153,
            molecular_weight_kg_per_mol=0.04409562,
        ),
        "i_butane": ComponentProperties(
            critical_temperature_k=408.2,
            critical_pressure_bara=36.5,
            acentric_factor=0.183,
            molecular_weight_kg_per_mol=0.05812220,
        ),
        "n_butane": ComponentProperties(
            critical_temperature_k=425.2,
            critical_pressure_bara=38.0,
            acentric_factor=0.199,
            molecular_weight_kg_per_mol=0.05812220,
        ),
        "i_pentane": ComponentProperties(
            critical_temperature_k=460.4,
            critical_pressure_bara=33.9,
            acentric_factor=0.227,
            molecular_weight_kg_per_mol=0.07214878,
        ),
        "n_pentane": ComponentProperties(
            critical_temperature_k=469.7,
            critical_pressure_bara=33.7,
            acentric_factor=0.251,
            molecular_weight_kg_per_mol=0.07214878,
        ),
        "n_hexane": ComponentProperties(
            critical_temperature_k=507.5,
            critical_pressure_bara=30.1,
            acentric_factor=0.299,
            molecular_weight_kg_per_mol=0.08617536,
        ),
    }

    @classmethod
    def get_component_molecular_weight(cls, component: str) -> float:
        """Retrieve the molecular weight for a given component."""
        try:
            return cls.COMPONENTS[component].molecular_weight_kg_per_mol
        except KeyError:
            raise ValueError(f"Molecular weight for component '{component}' is not defined.") from None
