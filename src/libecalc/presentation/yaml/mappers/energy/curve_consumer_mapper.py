from collections.abc import Mapping, Sequence

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.domain.resource import Resource
from libecalc.energy.models.curve_interpolator import CurveInterpolator
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlFuelTable, YamlPowerCurve
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import DataOrFile, YamlFile

POWER_HEADER = "POWER"
FUEL_HEADER = "FUEL"


def map_load_curve_model(
    unit_name: str,
    curve: DataOrFile[YamlPowerCurve],
    resources: Mapping[str, Resource],
) -> CurveInterpolator:
    return _build_model(
        unit_name=unit_name,
        curve=curve if isinstance(curve, YamlFile) else (curve.variable, curve.power),
        resources=resources,
        energy_header=POWER_HEADER,
    )


def map_rate_curve_model(
    unit_name: str,
    curve: DataOrFile[YamlFuelTable],
    resources: Mapping[str, Resource],
) -> CurveInterpolator:
    return _build_model(
        unit_name=unit_name,
        curve=curve if isinstance(curve, YamlFile) else (curve.variable, curve.fuel),
        resources=resources,
        energy_header=FUEL_HEADER,
    )


def _build_model(
    *,
    unit_name: str,
    curve: YamlFile | tuple[Sequence[float], Sequence[float]],
    resources: Mapping[str, Resource],
    energy_header: str,
) -> CurveInterpolator:
    """Build the interpolator from an inline (variable, energy) curve or a FILE. In a FILE, the energy
    column must be named exactly `energy_header` (case-insensitive); the other column can be named
    anything - it's the variable the curve is keyed on."""
    if isinstance(curve, YamlFile):
        resource = resources.get(curve.file)
        if resource is None:
            raise EcalcValidationException(f"'{unit_name}': FILE '{curve.file}' not found.")
        variable_header = _resolve_variable_header(unit_name, curve.file, resource.get_headers(), energy_header)
        try:
            variable_values = resource.get_float_column(variable_header)
            energy_values = resource.get_float_column(energy_header)
        except InvalidResourceException as e:
            raise EcalcValidationException(f"'{unit_name}': FILE '{curve.file}': {e}") from e
    else:
        variable_values, energy_values = curve

    try:
        return CurveInterpolator(variable_values=variable_values, energy_values=energy_values)
    except EcalcValidationException as e:
        source = f"FILE '{curve.file}': " if isinstance(curve, YamlFile) else ""
        raise EcalcValidationException(f"'{unit_name}': {source}{e}") from e


def _resolve_variable_header(unit_name: str, file_name: str, headers: list[str], energy_header: str) -> str:
    """Find the single non-energy column header in a two-column FILE, whatever it's named."""
    normalized = [header.upper() for header in headers]
    if len(headers) != 2 or energy_header not in normalized:
        raise EcalcValidationException(
            f"'{unit_name}': FILE '{file_name}' must have exactly two columns: {energy_header} and the "
            f"variable to interpolate on, got headers {headers}."
        )
    return next(header for header in headers if header.upper() != energy_header)
