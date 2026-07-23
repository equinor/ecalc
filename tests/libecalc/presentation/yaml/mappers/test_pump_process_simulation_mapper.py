from io import StringIO

import pytest

from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.yaml_entities import ResourceStream


def _pump_yaml_model(
    simple_yaml, configuration_service_factory, *, rate=None, pressure="10", density="1010", discharge="200"
):
    rate_expression = rate if rate is not None else "$var.produced_water_reinjection_total_system_rate_m3_per_day"
    yaml_text = (
        simple_yaml.main_file.read()
        + f"""

PUMP_PROCESS_SIMULATIONS:
  - TYPE: PUMP
    NAME: produced_water_reinjection
    PUMP_MODEL:
      CHART: pump_chart
    INLET:
      RATE: {rate_expression}
      PRESSURE: {pressure}
      DENSITY: {density}
    REQUIRED_DISCHARGE_PRESSURE: {discharge}
"""
    )
    configuration = configuration_service_factory(
        ResourceStream(name="pump_process.yaml", stream=StringIO(yaml_text))
    ).get_configuration()
    return YamlModel(
        configuration=configuration,
        resource_service=FileResourceService(
            working_directory=simple_yaml.main_file_path.parent,
            configuration=configuration,
        ),
    )


def test_pump_process_simulation_maps_and_evaluates(simple_yaml, configuration_service_factory):
    yaml_model = _pump_yaml_model(simple_yaml, configuration_service_factory)

    mapped_simulations = yaml_model.get_pump_process_simulations()

    assert len(mapped_simulations) == 1
    simulation, operating_inputs, periods = mapped_simulations[0]
    assert simulation.get_name() == "produced_water_reinjection"

    results = simulation.evaluate(operating_inputs)

    assert len(results) == len(operating_inputs) == len(periods)
    # Every evaluation carries a stream on every serial connection (off periods carry zero-flow streams).
    all_connections = {connection.get_id() for connection in simulation.get_process_unit_connections()}
    for result in results:
        assert set(result.connection_streams) == all_connections


@pytest.mark.parametrize(
    "rate, pressure, density, expected_subject",
    [
        ("100", "0", "1010", "suction pressure"),  # running period, invalid suction
        ("0", "0", "1010", "suction pressure"),  # suction is required even when the pump is off
        ("100", "10", "0", "inlet density"),  # density is always required
    ],
)
def test_pump_requires_positive_suction_and_density(
    simple_yaml, configuration_service_factory, rate, pressure, density, expected_subject
):
    yaml_model = _pump_yaml_model(
        simple_yaml, configuration_service_factory, rate=rate, pressure=pressure, density=density
    )

    with pytest.raises(EcalcValidationException, match=f"Pump {expected_subject} .* must be greater than 0"):
        yaml_model.get_pump_process_simulations()


def test_pump_rejects_non_positive_discharge_in_running_periods(simple_yaml, configuration_service_factory):
    yaml_model = _pump_yaml_model(simple_yaml, configuration_service_factory, rate="100", discharge="0")

    with pytest.raises(EcalcValidationException, match="Pump required discharge pressure .* must be greater than 0"):
        yaml_model.get_pump_process_simulations()


def test_pump_off_periods_allow_invalid_discharge(simple_yaml, configuration_service_factory):
    # Rate 0 -> pump off. A zero required discharge is tolerated; the outlet takes the inlet pressure.
    yaml_model = _pump_yaml_model(simple_yaml, configuration_service_factory, rate="0", pressure="3", discharge="0")

    simulation, operating_inputs, _periods = yaml_model.get_pump_process_simulations()[0]
    results = simulation.evaluate(operating_inputs)

    assert len(results) > 0
    for result in results:
        assert result.pump_result.shaft_power_mw == 0.0
        assert result.pump_result.operational_discharge_pressure_bara == pytest.approx(3.0)
