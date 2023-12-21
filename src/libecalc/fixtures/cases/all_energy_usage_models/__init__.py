from pathlib import Path

import pytest

from libecalc.fixtures import YamlCase
from libecalc.fixtures.case_utils import YamlCaseLoader

from .all_models_dto import (
    all_energy_usage_models_dto,
    compressor,
    compressor_system,
    compressor_system_variable_speed_compressor_trains,
    compressor_system_variable_speed_compressor_trains_multiple_suction_discharge_pressures,
    compressor_systems_and_compressor_train_temporal_dto,
    deh,
    flare,
    generic_from_design_point_compressor_train_consumer,
    genset_sampled,
    late_start_consumer,
    late_start_consumer_evolving_type,
    methane_venting,
    pump_system_el_consumer,
    salt_water_injection_tabular,
    simplified_compressor_system,
    simplified_compressor_train_predefined_variable_speed_charts_with_gerg_fluid,
    simplified_variable_speed_compressor_train_known_stages_consumer,
    simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model,
    simplified_variable_speed_compressor_train_unknown_stages_consumer,
    single_speed_compressor_train_asv_pressure_control,
    single_speed_compressor_train_downstream_choke_pressure_control,
    single_speed_compressor_train_downstream_choke_pressure_control_maximum_discharge_pressure,
    single_speed_compressor_train_upstream_choke_pressure_control,
    tabulated,
    turbine_driven_compressor_train,
    variable_speed_compressor_train_multiple_input_streams_and_interstage_pressure,
    variable_speed_compressor_train_predefined_charts,
    water_injection_single_speed,
    water_injection_variable_speed,
)
from .conftest import (
    all_energy_usage_models_variables,
    compressor_sampled_1d,
    compressor_train_variable_speed_user_defined_fluid_and_compressor_chart_and_turbine2,
    compressor_with_turbine,
    methane_values,
    regularity,
    simplified_variable_speed_compressor_train_known_stages,
    simplified_variable_speed_compressor_train_with_gerg_fluid2,
    single_speed_pump,
    turbine_dto,
    user_defined_single_speed_compressor_chart_dto,
    variable_speed_pump,
)

"""
Test project for All Energy Usage Models

The purpose of this fixture is to try to cover as many different energy usage models as possible from yaml to result.

"""


@pytest.fixture
def all_energy_usage_models_yaml() -> YamlCase:
    return YamlCaseLoader.load(
        case_path=Path(__file__).parent / "data",
        main_file="all_energy_usage_models.yaml",
        resource_names=[
            "einput/predefined_compressor_chart_curves.csv",
            "einput/genset.csv",
            "einput/pump_tabular.csv",
            "einput/pumpchart.csv",
            "einput/pumpchart_variable_speed.csv",
            "einput/compressor_sampled_1d.csv",
            "einput/tabular.csv",
            "sim/base_profile.csv",
            "sim/flare.csv",
        ],
    )
