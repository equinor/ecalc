from libecalc.presentation.yaml.yaml_entities import MemoryResource


def el2fuel_factory(electricity: list[float] = None, fuel: list[float] = None) -> MemoryResource:
    if electricity is None:
        electricity = [1, 2, 3, 4, 5]

    if fuel is None:
        fuel = [el * 2 for el in electricity]

    return MemoryResource(headers=["POWER", "FUEL"], data=[electricity, fuel])
