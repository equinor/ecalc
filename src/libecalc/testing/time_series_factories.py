from datetime import datetime

from libecalc.presentation.yaml.yaml_entities import MemoryResource


def production_profile_factory(timesteps: list[datetime] = None, **kwargs: list[float | int]):
    if timesteps is None:
        timesteps = [datetime(2020 + i, 1, 1) for i in range(1, 5)]

    if len(kwargs) == 0:
        columns = {"produced_oil": [i + 1 for i in range(len(timesteps))]}
    else:
        columns = kwargs

    headers = ["Date", *columns.keys()]
    data = [[timestep.strftime("%Y-%m-%d") for timestep in timesteps], *columns.values()]

    return MemoryResource(headers=headers, data=data)
