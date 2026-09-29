from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.domain.resource import Resource
from libecalc.energy.energy_types import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.models.tabular import TabularModel
from libecalc.presentation.yaml.domain.energy import TabularDemand, TimeSeriesConsumer
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlTabularConsumer

_FUEL = EcalcYamlKeywords.consumer_tabular_fuel
_POWER = EcalcYamlKeywords.consumer_tabular_power


def _load_model(resource: Resource, energy_header: str) -> TabularModel:
    variables = {
        header: resource.get_float_column(header) for header in resource.get_headers() if header != energy_header
    }
    return TabularModel(
        variables=variables, function_values=resource.get_float_column(energy_header), function_name=energy_header
    )


def _check_variables_given(unit: YamlTabularConsumer, tabulated: set[str]) -> None:
    given = set(unit.variables)
    if not_tabulated := sorted(given - tabulated):
        raise EcalcValidationException(
            f"'{unit.name}': {', '.join(not_tabulated)} given, but not tabulated in '{unit.file}'."
        )
    if missing := sorted(tabulated - given):
        raise EcalcValidationException(
            f"'{unit.name}': '{unit.file}' tabulates {', '.join(missing)}, which must be given."
        )


def _load_tabular_consumer(
    unit: YamlTabularConsumer, resource: Resource, upstream_output_type: type[Energy]
) -> tuple[TabularModel, type[Energy]]:
    """Return the table and the energy type the consumer draws from its input."""
    headers = resource.get_headers()
    upper_headers = [header.upper() for header in headers]
    if duplicated := sorted({header for header in upper_headers if upper_headers.count(header) > 1}):
        raise EcalcValidationException(
            f"'{unit.name}': '{unit.file}' has columns that differ only by case: {', '.join(duplicated)}."
        )
    power_header = next((header for header in headers if header.upper() == _POWER), None)
    fuel_header = next((header for header in headers if header.upper() == _FUEL), None)
    if power_header and fuel_header:
        raise EcalcValidationException(
            f"'{unit.name}': '{unit.file}' must have either a {_FUEL} or a {_POWER} column, not both."
        )
    if power_header:
        energy_header = power_header
        if upstream_output_type not in (ElectricalPower, MechanicalPower):
            raise EcalcValidationException(
                f"'{unit.name}': a power consumer must be fed electrical or mechanical power, "
                f"but INPUT '{unit.input}' provides {upstream_output_type.__name__}."
            )
        input_energy_type = upstream_output_type
    elif fuel_header:
        energy_header = fuel_header
        if upstream_output_type not in (FuelGasRate, DieselRate):
            raise EcalcValidationException(
                f"'{unit.name}': a fuel consumer must be fed FuelGasRate or DieselRate, "
                f"but INPUT '{unit.input}' provides {upstream_output_type.__name__}."
            )
        input_energy_type = upstream_output_type
    else:
        raise EcalcValidationException(
            f"'{unit.name}': '{unit.file}' must have a {_FUEL} or {_POWER} column, got {headers}."
        )

    _check_variables_given(unit, {header for header in headers if header != energy_header})
    try:
        return _load_model(resource, energy_header), input_energy_type
    except (EcalcValidationException, InvalidResourceException) as e:
        raise EcalcValidationException(f"'{unit.name}': invalid tabular file '{unit.file}': {e}") from e


def map_tabular_consumer(
    unit: YamlTabularConsumer,
    energy_unit_id: EnergyUnitId,
    resource: Resource,
    upstream_output_type: type[Energy],
    variables: dict[str, TimeSeriesExpression],
) -> TimeSeriesConsumer:
    model, input_energy_type = _load_tabular_consumer(unit, resource, upstream_output_type)
    return TimeSeriesConsumer(
        name=unit.name,
        energy_unit_id=energy_unit_id,
        demand=TabularDemand(name=unit.name, energy_type=input_energy_type, model=model, variables=variables),
    )
