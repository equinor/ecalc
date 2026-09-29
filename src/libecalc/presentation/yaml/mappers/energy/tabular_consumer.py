from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import EcalcError
from libecalc.domain.resource import Resource
from libecalc.energy.energy_types import DieselRate, ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.models.tabular import TabularModel
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlTabularConsumer

_FUEL = EcalcYamlKeywords.consumer_tabular_fuel
_POWER = EcalcYamlKeywords.consumer_tabular_power


def _load_model(resource: Resource, energy_header: str) -> TabularModel:
    variables = {
        header: resource.get_float_column(header) for header in resource.get_headers() if header != energy_header
    }
    return TabularModel(variables=variables, function_values=resource.get_float_column(energy_header))


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


def load_tabular_consumer(
    unit: YamlTabularConsumer, resource: Resource, upstream_output_type: type[Energy]
) -> tuple[TabularModel, type[Energy]]:
    """Return the table and the energy type the consumer draws from its input."""
    headers = resource.get_headers()
    if _POWER in headers and _FUEL in headers:
        raise EcalcValidationException(
            f"'{unit.name}': '{unit.file}' must have either a {_FUEL} or a {_POWER} column, not both."
        )
    if _POWER in headers:
        energy_header = _POWER
        if upstream_output_type not in (ElectricalPower, MechanicalPower):
            raise EcalcValidationException(
                f"'{unit.name}': a power consumer must be fed electrical or mechanical power, "
                f"but INPUT '{unit.input}' provides {upstream_output_type.__name__}."
            )
        input_energy_type = upstream_output_type
    elif _FUEL in headers:
        energy_header = _FUEL
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
    except EcalcError as e:
        raise EcalcValidationException(f"'{unit.name}': invalid tabular file '{unit.file}': {e}") from e
