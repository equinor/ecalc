"""
Constants and properties used in thermodynamic calculations.
"""


class ThermodynamicConstants:
    """Constants used in thermodynamic calculations."""

    # Gas constant in various units
    R_J_PER_MOL_K = 8.31446261815324  # J/(mol·K)

    # Critical properties for common components (Tc in K, Pc in bara)
    CRITICAL_PROPERTIES = {
        "nitrogen": {"Tc": 126.2, "Pc": 33.9, "omega": 0.039},
        "CO2": {"Tc": 304.1, "Pc": 73.8, "omega": 0.239},
        "methane": {"Tc": 190.4, "Pc": 46.0, "omega": 0.011},
        "ethane": {"Tc": 305.4, "Pc": 48.8, "omega": 0.099},
        "propane": {"Tc": 369.8, "Pc": 42.5, "omega": 0.153},
        "i_butane": {"Tc": 408.2, "Pc": 36.5, "omega": 0.183},
        "n_butane": {"Tc": 425.2, "Pc": 38.0, "omega": 0.199},
        "i_pentane": {"Tc": 460.4, "Pc": 33.9, "omega": 0.227},
        "n_pentane": {"Tc": 469.7, "Pc": 33.7, "omega": 0.251},
        "n_hexane": {"Tc": 507.5, "Pc": 30.1, "omega": 0.299},
        "water": {"Tc": 647.3, "Pc": 221.2, "omega": 0.344},
    }

    # Critical Z-factors for common components
    CRITICAL_Z_FACTORS = {
        "nitrogen": 0.29049,
        "CO2": 0.27414,
        "methane": 0.28737,
        "ethane": 0.28465,
        "propane": 0.28029,
        "i_butane": 0.28272,
        "n_butane": 0.27406,
        "i_pentane": 0.27052,
        "n_pentane": 0.26270,
        "n_hexane": 0.26037,
        "water": 0.229,  # Estimated value for water
    }

    # Specific heat capacity coefficients (Cp = a + b*T + c*T^2 + d*T^3) [J/(mol·K)]
    CP_COEFFICIENTS = {
        "nitrogen": {"a": 28.98, "b": 1.853e-3, "c": -9.647e-6, "d": 16.64e-9},
        "CO2": {"a": 22.26, "b": 5.981e-2, "c": -3.501e-5, "d": 7.469e-9},
        "methane": {"a": 19.25, "b": 5.213e-2, "c": 1.197e-5, "d": -1.132e-8},
        "ethane": {"a": 5.409, "b": 1.781e-1, "c": -6.938e-5, "d": 8.713e-9},
        "propane": {"a": 5.616, "b": 2.300e-1, "c": -8.824e-5, "d": 1.097e-8},
        "i_butane": {"a": 4.872, "b": 3.063e-1, "c": -1.571e-4, "d": 3.196e-8},
        "n_butane": {"a": 9.487, "b": 3.313e-1, "c": -1.108e-4, "d": -2.822e-9},
        "i_pentane": {"a": 6.774, "b": 4.445e-1, "c": -2.300e-4, "d": 4.658e-8},
        "n_pentane": {"a": 6.771, "b": 4.541e-1, "c": -2.264e-4, "d": 4.403e-8},
        "n_hexane": {"a": 6.938, "b": 5.548e-1, "c": -2.830e-4, "d": 5.723e-8},
        "water": {"a": 32.24, "b": 1.924e-3, "c": 1.055e-5, "d": -3.596e-9},
    }

    # Molecular weights [kg/mol]
    MOL_WEIGHTS = {
        "water": 0.01801534,
        "nitrogen": 0.02801340,
        "CO2": 0.04400995,
        "methane": 0.01604246,
        "ethane": 0.03006904,
        "propane": 0.04409562,
        "i_butane": 0.05812220,
        "n_butane": 0.05812220,
        "i_pentane": 0.07214878,
        "n_pentane": 0.07214878,
        "n_hexane": 0.08617536,
    }
