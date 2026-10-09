from collections.abc import Callable, Mapping, Sequence

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.errors.exceptions import InvalidResourceException
from libecalc.domain.resource import Resource
from libecalc.presentation.yaml.yaml_types.yaml_data_or_file import YamlFile


def map_curve_model[Model](
    *,
    unit_name: str,
    curve: YamlFile | tuple[Sequence[float], Sequence[float]],
    resources: Mapping[str, Resource],
    x_header: str,
    y_header: str,
    build: Callable[[Sequence[float], Sequence[float]], Model],
) -> Model:
    """Build a model from an inline (x, y) curve or a FILE, naming the unit and file in errors."""
    if isinstance(curve, YamlFile):
        resource = resources.get(curve.file)
        if resource is None:
            raise EcalcValidationException(f"'{unit_name}': FILE '{curve.file}' not found.")
        try:
            xs = resource.get_float_column(x_header)
            ys = resource.get_float_column(y_header)
        except InvalidResourceException as e:
            raise EcalcValidationException(f"'{unit_name}': FILE '{curve.file}': {e}") from e
    else:
        xs, ys = curve

    try:
        return build(xs, ys)
    except EcalcValidationException as e:
        source = f"FILE '{curve.file}': " if isinstance(curve, YamlFile) else ""
        raise EcalcValidationException(f"'{unit_name}': {source}{e}") from e
