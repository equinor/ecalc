from libecalc.common.math.numbers import Numbers


def round_values(value, precision=6):
    """Round the numeric values in the result to the specified precision."""
    return Numbers.format_results_to_precision(value, precision)
