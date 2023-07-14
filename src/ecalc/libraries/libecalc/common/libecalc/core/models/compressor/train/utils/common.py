from dataclasses import dataclass
from typing import Tuple

import pandas as pd
import xgboost as xgb
from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.core.models.compressor.train.fluid import FluidStream
from libecalc.core.models.compressor.train.utils.enthalpy_calculations import (
    calculate_outlet_pressure_campbell,
)

# sys.path.insert(1, "src/ecalc/libraries/libecalc/common/libecalc/core/models/compressor/train/utils")
from mlp_predict import NeuralNet

OUTLET_PRESSURE_CONVERGENCE_TOLERANCE = 1e-2
PRESSURE_CALCULATION_TOLERANCE = 1e-3
POWER_CALCULATION_TOLERANCE = 1e-3


def calculate_asv_corrected_rate(
    minimum_actual_rate_m3_per_hour: float,
    actual_rate_m3_per_hour: float,
    density_kg_per_m3,
) -> Tuple[float, float]:
    actual_rate_asv_corrected_m3_per_hour = max(actual_rate_m3_per_hour, minimum_actual_rate_m3_per_hour)
    mass_rate_asv_corrected_kg_per_hour = actual_rate_asv_corrected_m3_per_hour * density_kg_per_m3
    return (
        actual_rate_asv_corrected_m3_per_hour,
        mass_rate_asv_corrected_kg_per_hour,
    )


def calculate_power_in_megawatt(
    enthalpy_change_J_per_kg: float,
    mass_rate_kg_per_hour: float,
) -> float:
    return (
        enthalpy_change_J_per_kg
        * mass_rate_kg_per_hour
        / UnitConstants.SECONDS_PER_HOUR
        * UnitConstants.WATT_TO_MEGAWATT
    )


# Choose what model to run with
ml_model = "neqsim"

rgs = xgb.XGBRegressor()
rgs.load_model(
    "src/ecalc/libraries/libecalc/common/libecalc/core/models/compressor/train/utils/ml_configs/XGBoost.json"
)

nn_model = NeuralNet(
    "src/ecalc/libraries/libecalc/common/libecalc/core/models/compressor/train/utils/final_model/model.pt"
)
nn_model.mlp.eval()


# Dataclass to more easily retrieve kappa and Z values
@dataclass
class Outlet_values:
    kappa: float
    z: float


# Method that changes
def ml_ph_flash_xgb(pressure_2: float, dataframe):
    # Change P_2 value
    dataframe.at[0, "pressure_2"] = pressure_2

    pred = rgs.predict(dataframe)

    print(pred)

    kappa = pred[:, 2]
    z = pred[:, 1]

    return Outlet_values(kappa, z)


def ml_ph_flash_nn(pressure_2: float, dataframe):
    # Change P_2 value
    dataframe.at[0, "pressure_2"] = pressure_2
    outlet_z, outlet_kappa = nn_model.predict(dataframe)

    return Outlet_values(outlet_kappa, outlet_z)


# To more easily facilitate the ml changes, we only calculate the Kappa and Z values and use these values directly,
# instead of updating the stream with these values each iteration
def calculate_outlet_pressure_and_stream(
    polytropic_efficiency: float,
    polytropic_head_joule_per_kg: float,
    inlet_stream: FluidStream,
) -> Tuple[float, FluidStream]:
    """

    Args:
        polytropic_efficiency: Allowed values (0, 1]
        polytropic_head_joule_per_kg:
        inlet_stream:

    Returns:

    """

    # Find EOS of fluid
    # eos = inlet_stream.fluid_model.eos_model
    # print(str(eos))

    if ml_model == "xgb":
        iterative_function = ml_ph_flash_xgb

        # iterative_output: outlet_values

    elif ml_model == "nn":
        iterative_function = ml_ph_flash_nn

    else:
        iterative_function = inlet_stream.set_new_pressure_and_enthalpy_change
        # iterative_output: FluidStream

    comp_dict = dict(inlet_stream.fluid_model.composition)
    composition_df = pd.DataFrame([comp_dict])
    composition_df /= 100

    outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa = calculate_outlet_pressure_campbell(
        kappa=inlet_stream.kappa,
        polytropic_efficiency=polytropic_efficiency,
        polytropic_head_fluid_Joule_per_kg=polytropic_head_joule_per_kg,
        molar_mass=inlet_stream.molar_mass_kg_per_mol,
        z_inlet=inlet_stream.z,
        inlet_temperature_K=inlet_stream.temperature_kelvin,
        inlet_pressure_bara=inlet_stream.pressure_bara,
    )
    inlet_enthalpy = inlet_stream._neqsim_fluid_stream.enthalpy_joule_per_kg
    # print(inlet_enthalpy)

    df = pd.DataFrame(
        {
            "pressure_2": [outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa],
            "enthalpy_2": [(polytropic_head_joule_per_kg / polytropic_efficiency) + inlet_enthalpy],
        }
    )
    X_test = pd.concat([df, composition_df], axis=1)

    if ml_model == "xgb" or ml_model == "nn":
        args = [outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa, X_test]
    else:
        args = [
            outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa,
            polytropic_head_joule_per_kg / polytropic_efficiency,
        ]

    iterative_output = iterative_function(*args)

    # outlet_kappa, outlet_z = ml_ph_flash_xgb
    # (
    # inlet_stream, outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa, X_test
    # )

    """
    outlet_stream_compressor_current_iteration = inlet_stream.set_new_pressure_and_enthalpy_change(
        new_pressure=outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa,
        enthalpy_change_joule_per_kg=polytropic_head_joule_per_kg / polytropic_efficiency,
    )
    """

    outlet_pressure_this_stage_bara = outlet_pressure_this_stage_bara_based_on_inlet_z_and_kappa * 0.95
    converged = False
    i = 0
    max_iterations = 20
    while not converged and i < max_iterations:
        z_average = (inlet_stream.z + iterative_output.z) / 2.0
        kappa_average = (inlet_stream.kappa + iterative_output.kappa) / 2.0
        outlet_pressure_previous = outlet_pressure_this_stage_bara
        outlet_pressure_this_stage_bara = calculate_outlet_pressure_campbell(
            kappa=kappa_average,
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_fluid_Joule_per_kg=polytropic_head_joule_per_kg,
            molar_mass=inlet_stream.molar_mass_kg_per_mol,
            z_inlet=z_average,
            inlet_temperature_K=inlet_stream.temperature_kelvin,
            inlet_pressure_bara=inlet_stream.pressure_bara,
        )

        args[0] = outlet_pressure_this_stage_bara
        iterative_output = iterative_function(*args)

        # outlet_kappa, outlet_z = ml_ph_flash_xgb
        # (inlet_stream, outlet_pressure_this_stage_bara, X_test)
        """
        outlet_stream_compressor_current_iteration = inlet_stream.set_new_pressure_and_enthalpy_change(
            new_pressure=outlet_pressure_this_stage_bara,
            enthalpy_change_joule_per_kg=polytropic_head_joule_per_kg / polytropic_efficiency,
        )
        """

        # print("Average kappa = " + str(kappa_average))
        # print("Average Z= " + str(z_average))

        diff = abs(outlet_pressure_previous - outlet_pressure_this_stage_bara) / outlet_pressure_this_stage_bara

        converged = diff < OUTLET_PRESSURE_CONVERGENCE_TOLERANCE

        i += 1

        if i == max_iterations:
            logger.error(
                "calculate_outlet_pressure_and_stream"
                f" did not converge after {max_iterations} iterations."
                f" inlet_z: {inlet_stream.z}."
                f" inlet_kappa: {inlet_stream.kappa}."
                f" polytropic_efficiency: {polytropic_efficiency}."
                f" polytropic_head_joule_per_kg: {polytropic_head_joule_per_kg}."
                f" molar_mass_kg_per_mol: {inlet_stream.molar_mass_kg_per_mol}."
                f" inlet_temperature_kelvin: {inlet_stream.temperature_kelvin}."
                f" inlet_pressure_bara: {inlet_stream.pressure_bara}."
                f" Final diff between target and result was {diff}, while expected convergence diff criteria is set to diff lower than {OUTLET_PRESSURE_CONVERGENCE_TOLERANCE}"
                f" NOTE! We will use as the closest result we got for target for further calculations."
                " This should normally not happen. Please contact eCalc support."
            )
    # Use neqsim PH-flash at the end to activate all fluid properties
    outlet_stream_compressor_current_iteration = inlet_stream.set_new_pressure_and_enthalpy_change(
        new_pressure=outlet_pressure_this_stage_bara,
        enthalpy_change_joule_per_kg=polytropic_head_joule_per_kg / polytropic_efficiency,
    )

    return (
        outlet_pressure_this_stage_bara,
        outlet_stream_compressor_current_iteration,
    )
