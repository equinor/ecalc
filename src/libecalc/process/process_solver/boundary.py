from libecalc.common.ddd import value_object


@value_object
class Boundary:
    min: float
    max: float
