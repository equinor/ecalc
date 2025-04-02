from libecalc.presentation.yaml.resource import Resource


def validate_columns(resource: Resource):
    tmp_headers_always_float = ["SPEED", "RATE", "HEAD", "EFFICIENCY", "POWER", "FUEL"]
    # Valider for headers i compressor chart
    errors = {}
    for column in resource.get_headers():
        if column in tmp_headers_always_float:
            error_values = []
            for value in resource.get_column(column):
                try:
                    float(value)
                except ValueError:
                    error_values.append(value)
            if error_values:
                errors.update({column: error_values})

    if errors:
        msg = [f"column '{key}' with value(s) '{', '.join(values)}'" for key, values in errors.items()]

        # raise BadRequestException(
        raise ValueError(
            f"Found non-numeric values in {', '.join(msg)}. Please ensure values are numbers and try again!"
        )
